"""API routes for OpenSpool MQTT printer communication."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.mqtt.openspool import openspool_client
from backend.spool.database import get_db
from backend.spool import service

router = APIRouter(prefix="/api/mqtt", tags=["mqtt"])


class ConnectRequest(BaseModel):
    ip: str
    serial: str
    access_code: str


class SendFilamentRequest(BaseModel):
    slot: int  # AMS slot (0-3 or 0-15)
    material: str  # e.g. "PLA"
    color_hex: str  # e.g. "#FF0000"
    nozzle_temp_min: int
    nozzle_temp_max: int
    brand: str = "Generic"
    weight_g: int = 1000


class SendFromSpoolRequest(BaseModel):
    slot: int
    spool_id: int


class SavePrinterRequest(BaseModel):
    name: str
    ip: str
    serial: str
    access_code: str
    model: str = ""


@router.get("/status")
async def mqtt_status():
    """Get current MQTT connection status."""
    return openspool_client.printer_info


@router.post("/connect")
async def mqtt_connect(req: ConnectRequest):
    """Connect to a Bambu Lab printer via MQTT."""
    success = openspool_client.connect(req.ip, req.serial, req.access_code)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to connect to printer")
    return {"connected": True, "ip": req.ip, "serial": req.serial}


@router.post("/disconnect")
async def mqtt_disconnect():
    """Disconnect from the printer."""
    openspool_client.disconnect()
    return {"connected": False}


@router.post("/send")
async def send_filament(req: SendFilamentRequest):
    """Send filament data to the printer for a specific AMS slot."""
    if not openspool_client.is_connected:
        raise HTTPException(status_code=503, detail="Not connected to any printer")

    success = openspool_client.send_filament_data(
        slot=req.slot,
        material=req.material,
        color_hex=req.color_hex,
        nozzle_temp_min=req.nozzle_temp_min,
        nozzle_temp_max=req.nozzle_temp_max,
        brand=req.brand,
        weight_g=req.weight_g,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send filament data")
    return {"sent": True, "slot": req.slot}


@router.post("/send-spool")
async def send_spool(req: SendFromSpoolRequest, db: Session = Depends(get_db)):
    """Send filament data from a saved spool to the printer."""
    if not openspool_client.is_connected:
        raise HTTPException(status_code=503, detail="Not connected to any printer")

    spool = service.get_spool(db, req.spool_id)
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")

    success = openspool_client.send_filament_data(
        slot=req.slot,
        material=spool.material,
        color_hex=spool.color_hex,
        nozzle_temp_min=spool.nozzle_temp_min,
        nozzle_temp_max=spool.nozzle_temp_max,
        brand=spool.brand,
        weight_g=spool.weight_g,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send filament data")

    # Mark spool as recently used
    service.touch_spool(db, req.spool_id)
    return {"sent": True, "slot": req.slot, "spool": spool.to_dict()}


# ──────────────────────────────────────────────
# Saved printer configurations
# ──────────────────────────────────────────────

@router.get("/printers")
async def list_printers(db: Session = Depends(get_db)):
    """List saved printer configurations."""
    printers = service.get_all_printers(db)
    return {"printers": [p.to_dict() for p in printers]}


@router.post("/printers")
async def save_printer(req: SavePrinterRequest, db: Session = Depends(get_db)):
    """Save a printer configuration."""
    printer = service.create_printer(db, req.model_dump())
    return printer.to_dict()


@router.delete("/printers/{printer_id}")
async def delete_printer(printer_id: int, db: Session = Depends(get_db)):
    """Delete a saved printer configuration."""
    if not service.delete_printer(db, printer_id):
        raise HTTPException(status_code=404, detail="Printer not found")
    return {"deleted": True}
