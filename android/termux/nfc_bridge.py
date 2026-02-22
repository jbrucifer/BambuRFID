#!/usr/bin/env python3
"""
BambuNFC Bridge — Termux Edition

A lightweight NFC bridge that runs on Android via Termux.
Connects to the BambuRFID server and relays NFC read/write commands
using Termux's NFC API.

Setup:
    pkg install python termux-api
    pip install websocket-client
    python nfc_bridge.py <server_ip:port>

Usage:
    python nfc_bridge.py 192.168.1.197:8000
"""

import json
import subprocess
import sys
import time
import threading

try:
    import websocket
except ImportError:
    print("Installing websocket-client...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client"])
    import websocket


def termux_nfc_scan():
    """
    Use Termux API to scan an NFC tag.
    Returns the tag data as a dict, or None if failed.
    """
    try:
        result = subprocess.run(
            ["termux-nfc", "-t", "MifareClassic"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return None
    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        print("[ERROR] termux-nfc not found. Install Termux:API:")
        print("  pkg install termux-api")
        print("  Also install the Termux:API app from F-Droid")
        return None
    except Exception as e:
        print(f"[ERROR] NFC scan failed: {e}")
        return None


def termux_toast(msg):
    """Show a toast notification on the phone."""
    try:
        subprocess.run(["termux-toast", msg], timeout=5)
    except Exception:
        pass


class NFCBridge:
    def __init__(self, server_url):
        self.server_url = server_url
        self.ws = None
        self.running = True
        self.pending_action = None
        self.pending_request_id = None

    def connect(self):
        ws_url = self.server_url
        if not ws_url.startswith("ws"):
            ws_url = f"ws://{ws_url}/ws/nfc"
        if not "/ws/" in ws_url:
            ws_url = f"{ws_url}/ws/nfc"

        print(f"Connecting to {ws_url}...")
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.run_forever()

    def on_open(self, ws):
        print("[CONNECTED] Bridge connected to BambuRFID server")
        termux_toast("BambuNFC Bridge connected!")
        self.send({
            "action": "STATUS",
            "connected": True,
            "device": "Termux NFC Bridge",
        })

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            action = data.get("action", "")

            if action == "READ_TAG":
                self.pending_action = "READ_TAG"
                self.pending_request_id = data.get("request_id", "")
                print("\n[READ] Server requested tag read")
                print("       Hold a tag near the phone...")
                termux_toast("Tap NFC tag to read")
                threading.Thread(target=self.do_read, daemon=True).start()

            elif action == "WRITE_TAG":
                self.pending_request_id = data.get("request_id", "")
                print("\n[WRITE] Server requested tag write")
                print("        Hold a blank tag near the phone...")
                termux_toast("Tap NFC tag to write")
                # Note: Termux NFC write is limited — notify user
                self.send({
                    "action": "ERROR",
                    "message": "Termux NFC write is not fully supported. Use the native APK for write operations.",
                    "request_id": self.pending_request_id,
                })

            else:
                print(f"[MSG] {action}: {data}")

        except Exception as e:
            print(f"[ERROR] Message parse error: {e}")

    def do_read(self):
        """Perform NFC read in a background thread."""
        tag_data = termux_nfc_scan()
        if tag_data:
            uid = tag_data.get("uid", tag_data.get("id", ""))
            print(f"[TAG] Read tag: UID={uid}")
            termux_toast(f"Tag read: {uid}")

            # Extract block data if available
            blocks = tag_data.get("sectors", [])
            block_list = []
            if blocks:
                import base64
                for sector in blocks:
                    for block in sector.get("blocks", []):
                        block_bytes = bytes.fromhex(block.get("data", "00" * 16))
                        block_list.append(base64.b64encode(block_bytes).decode())

            self.send({
                "action": "TAG_DATA",
                "uid": uid,
                "blocks": block_list,
                "request_id": self.pending_request_id or "",
                "raw": tag_data,
            })
        else:
            print("[TAG] No tag detected or read failed")
            self.send({
                "action": "ERROR",
                "message": "No tag detected or NFC read failed",
                "request_id": self.pending_request_id or "",
            })

        self.pending_action = None
        self.pending_request_id = None

    def on_error(self, ws, error):
        print(f"[ERROR] WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"[DISCONNECTED] Connection closed")
        if self.running:
            print("Reconnecting in 5 seconds...")
            time.sleep(5)
            self.connect()

    def send(self, data):
        if self.ws:
            self.ws.send(json.dumps(data))

    def run(self):
        print("=" * 50)
        print("  BambuNFC Bridge — Termux Edition")
        print("=" * 50)
        print()
        print(f"Server: {self.server_url}")
        print()
        print("This bridges your phone's NFC to the BambuRFID")
        print("web server. Keep this running while using the app.")
        print()
        print("Press Ctrl+C to stop.")
        print()

        try:
            self.connect()
        except KeyboardInterrupt:
            self.running = False
            print("\nStopped.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python nfc_bridge.py <server_ip:port>")
        print("Example: python nfc_bridge.py 192.168.1.197:8000")
        sys.exit(1)

    server = sys.argv[1]
    bridge = NFCBridge(server)
    bridge.run()
