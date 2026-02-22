"""Application configuration."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
DATABASE_URL = f"sqlite:///{BASE_DIR / 'spools.db'}"

# NFC Bridge WebSocket
NFC_BRIDGE_HOST = os.getenv("NFC_BRIDGE_HOST", "0.0.0.0")
NFC_BRIDGE_PORT = int(os.getenv("NFC_BRIDGE_PORT", "8000"))

# MQTT / OpenSpool defaults
MQTT_PORT = 8883
MQTT_USERNAME = "bblp"
