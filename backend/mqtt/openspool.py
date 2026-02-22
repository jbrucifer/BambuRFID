"""
OpenSpool MQTT client for communicating filament data to Bambu Lab printers.

Bypasses the RFID tag requirement by sending filament information directly
to the printer over MQTT (TLS on port 8883).

Requirements:
- Printer must have LAN Mode enabled
- Printer must have Developer Mode enabled (some models)
- Connection uses username "bblp" and the printer's LAN access code

Reference: https://github.com/spuder/OpenSpool
"""

import json
import logging
import ssl
from typing import Optional

import paho.mqtt.client as mqtt

from backend.config import MQTT_PORT, MQTT_USERNAME

logger = logging.getLogger(__name__)


class OpenSpoolClient:
    """MQTT client for pushing filament data to Bambu Lab printers."""

    def __init__(self):
        self._client: Optional[mqtt.Client] = None
        self._connected = False
        self._printer_serial: str = ""
        self._printer_ip: str = ""

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def printer_info(self) -> dict:
        return {
            "connected": self._connected,
            "ip": self._printer_ip,
            "serial": self._printer_serial,
        }

    def connect(self, ip: str, serial: str, access_code: str) -> bool:
        """
        Connect to a Bambu Lab printer's MQTT broker.

        Args:
            ip: Printer IP address.
            serial: Printer serial number.
            access_code: LAN access code from printer settings.

        Returns:
            True if connection was successful.
        """
        try:
            self.disconnect()

            self._printer_ip = ip
            self._printer_serial = serial

            self._client = mqtt.Client(
                client_id=f"bambu_rfid_{serial}",
                protocol=mqtt.MQTTv311,
            )

            # TLS configuration — Bambu printers use self-signed certificates
            self._client.tls_set(cert_reqs=ssl.CERT_NONE)
            self._client.tls_insecure_set(True)

            self._client.username_pw_set(MQTT_USERNAME, access_code)

            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message

            self._client.connect(ip, MQTT_PORT, keepalive=60)
            self._client.loop_start()
            return True

        except Exception as e:
            logger.error(f"MQTT connect failed: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Disconnect from the printer."""
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
        self._connected = False

    def send_filament_data(self, slot: int, material: str, color_hex: str,
                           nozzle_temp_min: int, nozzle_temp_max: int,
                           brand: str = "Generic",
                           weight_g: int = 1000) -> bool:
        """
        Push filament information to the printer for a specific AMS slot.

        Args:
            slot: AMS slot number (0-3 for AMS Lite, 0-15 for AMS Pro).
            material: Material type string (e.g. "PLA", "PETG").
            color_hex: Color as hex string (e.g. "FF0000" for red).
            nozzle_temp_min: Minimum nozzle temperature °C.
            nozzle_temp_max: Maximum nozzle temperature °C.
            brand: Filament brand name.
            weight_g: Spool weight in grams.

        Returns:
            True if message was published successfully.
        """
        if not self._client or not self._connected:
            logger.error("Not connected to printer")
            return False

        # Remove '#' prefix from color if present
        color = color_hex.lstrip("#")

        payload = {
            "print": {
                "command": "ams_filament_setting",
                "ams_id": slot // 4,
                "tray_id": slot % 4,
                "tray_color": f"{color}FF",  # Add alpha
                "nozzle_temp_min": nozzle_temp_min,
                "nozzle_temp_max": nozzle_temp_max,
                "tray_type": material,
                "setting_id": "",
                "reason": "success",
                "result": "success",
            }
        }

        topic = f"device/{self._printer_serial}/request"
        try:
            result = self._client.publish(topic, json.dumps(payload))
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Sent filament data for slot {slot}: {material} ({color})")
                return True
            else:
                logger.error(f"MQTT publish failed: rc={result.rc}")
                return False
        except Exception as e:
            logger.error(f"MQTT publish error: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            logger.info(f"Connected to printer at {self._printer_ip}")
            # Subscribe to printer reports
            topic = f"device/{self._printer_serial}/report"
            client.subscribe(topic)
        else:
            self._connected = False
            logger.error(f"MQTT connection refused: rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnect: rc={rc}")

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
            logger.debug(f"Printer message: {data}")
        except json.JSONDecodeError:
            pass


# Global singleton
openspool_client = OpenSpoolClient()
