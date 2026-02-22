"""API routes for NFC bridge management."""

from fastapi import APIRouter, WebSocket

from backend.bridge.nfc_bridge import nfc_bridge

router = APIRouter(tags=["bridge"])


@router.websocket("/ws/nfc")
async def nfc_websocket(websocket: WebSocket):
    """WebSocket endpoint for the Android NFC bridge app."""
    await nfc_bridge.connect(websocket)
    await nfc_bridge.listen(websocket)


@router.get("/api/bridge/status")
async def bridge_status():
    """Check if the NFC bridge phone is connected."""
    return {"connected": nfc_bridge.is_connected}
