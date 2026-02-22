"""
WebSocket server for the Android NFC bridge.

The Android companion app connects to this WebSocket endpoint and acts as
a MIFARE Classic NFC reader/writer, relaying raw block data between the
phone's NFC hardware and the web backend.

Protocol messages (JSON):
  Backend → Phone:
    {"action": "READ_TAG"}
    {"action": "WRITE_TAG", "keys": [...], "blocks": [...]}
    {"action": "DERIVE_KEYS", "uid": "..."}

  Phone → Backend:
    {"action": "TAG_DATA", "uid": "...", "blocks": [...]}
    {"action": "WRITE_RESULT", "success": true/false, "error": "..."}
    {"action": "TAG_DETECTED", "uid": "..."}
    {"action": "STATUS", "connected": true, "device": "..."}
    {"action": "ERROR", "message": "..."}
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Awaitable

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class NFCBridgeManager:
    """Manages WebSocket connections from Android NFC bridge apps."""

    def __init__(self):
        self._phone: Optional[WebSocket] = None
        self._pending_reads: dict[str, asyncio.Future] = {}
        self._pending_writes: dict[str, asyncio.Future] = {}
        self._on_tag_data: Optional[Callable[[dict], Awaitable[None]]] = None
        self._request_counter = 0

    @property
    def is_connected(self) -> bool:
        return self._phone is not None

    async def connect(self, websocket: WebSocket):
        """Accept a new phone connection (replaces any existing one)."""
        await websocket.accept()
        if self._phone:
            try:
                await self._phone.close()
            except Exception:
                pass
        self._phone = websocket
        logger.info("NFC bridge phone connected")

    async def disconnect(self):
        """Handle phone disconnection."""
        self._phone = None
        # Cancel pending futures
        for fut in self._pending_reads.values():
            if not fut.done():
                fut.cancel()
        for fut in self._pending_writes.values():
            if not fut.done():
                fut.cancel()
        self._pending_reads.clear()
        self._pending_writes.clear()
        logger.info("NFC bridge phone disconnected")

    async def handle_message(self, data: dict):
        """Process an incoming message from the phone."""
        action = data.get("action", "")

        if action == "TAG_DATA":
            # Phone read a tag and is sending the data
            request_id = data.get("request_id", "")
            if request_id in self._pending_reads:
                self._pending_reads[request_id].set_result(data)
                del self._pending_reads[request_id]
            elif self._on_tag_data:
                await self._on_tag_data(data)

        elif action == "WRITE_RESULT":
            request_id = data.get("request_id", "")
            if request_id in self._pending_writes:
                self._pending_writes[request_id].set_result(data)
                del self._pending_writes[request_id]

        elif action == "TAG_DETECTED":
            logger.info(f"Tag detected: UID={data.get('uid', 'unknown')}")

        elif action == "STATUS":
            logger.info(f"Phone status: {data}")

        elif action == "ERROR":
            logger.error(f"Phone error: {data.get('message', 'unknown')}")
            # Fail any pending operations
            for fut in list(self._pending_reads.values()):
                if not fut.done():
                    fut.set_exception(Exception(data.get("message", "NFC error")))
            for fut in list(self._pending_writes.values()):
                if not fut.done():
                    fut.set_exception(Exception(data.get("message", "NFC error")))

    async def request_read(self, timeout: float = 30.0) -> dict:
        """
        Request the phone to read a tag.

        Returns the tag data dict with 'uid' and 'blocks' fields.
        Raises TimeoutError if no tag is read within the timeout.
        """
        if not self._phone:
            raise ConnectionError("No phone connected")

        self._request_counter += 1
        request_id = str(self._request_counter)

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_reads[request_id] = future

        await self._phone.send_json({
            "action": "READ_TAG",
            "request_id": request_id,
        })

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_reads.pop(request_id, None)
            raise TimeoutError("Tag read timed out — hold a tag near the phone")

    async def request_write(self, keys: list[str], blocks: list[str],
                            uid: Optional[str] = None, timeout: float = 30.0) -> dict:
        """
        Request the phone to write data to a tag.

        Args:
            keys: List of 16 hex-encoded sector keys.
            blocks: List of 64 base64-encoded block data.
            uid: Optional UID for magic tag UID writing.
            timeout: Seconds to wait for write completion.

        Returns the write result dict.
        """
        if not self._phone:
            raise ConnectionError("No phone connected")

        self._request_counter += 1
        request_id = str(self._request_counter)

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_writes[request_id] = future

        message = {
            "action": "WRITE_TAG",
            "request_id": request_id,
            "keys": keys,
            "blocks": blocks,
        }
        if uid:
            message["uid"] = uid

        await self._phone.send_json(message)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_writes.pop(request_id, None)
            raise TimeoutError("Tag write timed out — hold a tag near the phone")

    async def listen(self, websocket: WebSocket):
        """Main loop for handling phone WebSocket messages."""
        try:
            while True:
                text = await websocket.receive_text()
                data = json.loads(text)
                await self.handle_message(data)
        except WebSocketDisconnect:
            await self.disconnect()
        except Exception as e:
            logger.error(f"NFC bridge error: {e}")
            await self.disconnect()


# Global singleton
nfc_bridge = NFCBridgeManager()
