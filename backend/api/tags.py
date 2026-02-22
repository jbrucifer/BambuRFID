"""API routes for RFID tag operations — read, decode, encode, clone."""

import base64
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.crypto.kdf import derive_keys_from_hex, derive_keys
from backend.crypto.tag_auth import get_auth_payload
from backend.rfid.tag_parser import (
    parse_from_binary, parse_from_hex, parse_from_base64_blocks,
    parse_proxmark3_dump,
)
from backend.rfid.tag_builder import build_base64_blocks, build_hex, build_proxmark3_dump
from backend.rfid.bambu_format import FilamentData, build_tag_blocks
from backend.bridge.nfc_bridge import nfc_bridge
from backend.spool.database import get_db
from backend.spool import service as spool_service

router = APIRouter(prefix="/api/tags", tags=["tags"])


# ──────────────────────────────────────────────
# Request/Response models
# ──────────────────────────────────────────────

class DeriveKeysRequest(BaseModel):
    uid: str  # Hex string e.g. "7AD43F1C"


class DecodeHexRequest(BaseModel):
    hex_data: str


class DecodeBlocksRequest(BaseModel):
    blocks: list[str]  # Base64-encoded blocks


class DecodeProxmarkRequest(BaseModel):
    dump_text: str


class EncodeRequest(BaseModel):
    material_variant_id: str = ""
    material_id: str = ""
    filament_type: str = ""
    detailed_filament_type: str = ""
    color_hex: str = "#FFFFFF"
    color_alpha: int = 255
    spool_weight_g: int = 1000
    filament_diameter_mm: float = 1.75
    drying_temp_c: int = 0
    drying_time_h: int = 0
    bed_temp_type: int = 0
    bed_temp_c: int = 60
    max_hotend_temp_c: int = 230
    min_hotend_temp_c: int = 190
    nozzle_diameter: float = 0.4
    tray_uid: str = ""
    spool_width_mm: float = 0.0
    production_datetime: str = ""
    filament_length_m: int = 330

    # If cloning, include source tag data
    source_blocks: Optional[list[str]] = None  # Base64 blocks from source tag


class ReadTagRequest(BaseModel):
    timeout: float = 30.0


class WriteTagRequest(BaseModel):
    blocks: list[str]  # Base64-encoded blocks to write
    target_uid: Optional[str] = None  # For magic tag UID cloning


class CloneRequest(BaseModel):
    source_dump_id: Optional[int] = None  # Clone from saved dump
    timeout: float = 30.0


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@router.post("/derive-keys")
async def derive_keys_endpoint(req: DeriveKeysRequest):
    """Derive 16 sector keys from a tag UID."""
    try:
        keys = derive_keys_from_hex(req.uid)
        return {"uid": req.uid.upper(), "keys": keys}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/decode/hex")
async def decode_hex(req: DecodeHexRequest):
    """Decode a hex-encoded tag dump into filament data."""
    try:
        fd = parse_from_hex(req.hex_data)
        return fd.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/decode/blocks")
async def decode_blocks(req: DecodeBlocksRequest):
    """Decode base64-encoded blocks into filament data."""
    try:
        fd = parse_from_base64_blocks(req.blocks)
        return fd.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/decode/proxmark")
async def decode_proxmark(req: DecodeProxmarkRequest):
    """Decode a Proxmark3 text dump into filament data."""
    try:
        fd = parse_proxmark3_dump(req.dump_text)
        return fd.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/decode/file")
async def decode_file(file: UploadFile = File(...)):
    """Decode an uploaded binary tag dump file."""
    try:
        data = await file.read()
        fd = parse_from_binary(data)
        return fd.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/encode")
async def encode_tag(req: EncodeRequest):
    """Encode filament data into tag blocks."""
    try:
        fd = FilamentData()
        fd.material_variant_id = req.material_variant_id
        fd.material_id = req.material_id
        fd.filament_type = req.filament_type
        fd.detailed_filament_type = req.detailed_filament_type
        fd.spool_weight_g = req.spool_weight_g
        fd.filament_diameter_mm = req.filament_diameter_mm
        fd.drying_temp_c = req.drying_temp_c
        fd.drying_time_h = req.drying_time_h
        fd.bed_temp_type = req.bed_temp_type
        fd.bed_temp_c = req.bed_temp_c
        fd.max_hotend_temp_c = req.max_hotend_temp_c
        fd.min_hotend_temp_c = req.min_hotend_temp_c
        fd.nozzle_diameter = req.nozzle_diameter
        fd.tray_uid = req.tray_uid
        fd.spool_width_mm = req.spool_width_mm
        fd.production_datetime = req.production_datetime
        fd.filament_length_m = req.filament_length_m

        # Parse color
        color_hex = req.color_hex.lstrip("#")
        r = int(color_hex[0:2], 16) if len(color_hex) >= 2 else 0
        g = int(color_hex[2:4], 16) if len(color_hex) >= 4 else 0
        b = int(color_hex[4:6], 16) if len(color_hex) >= 6 else 0
        fd.color_rgba = bytes([r, g, b, req.color_alpha])

        # If cloning from source, use source blocks as base
        if req.source_blocks:
            fd.raw_blocks = [base64.b64decode(b) for b in req.source_blocks]

        blocks = build_base64_blocks(fd)
        hex_dump = build_hex(fd)
        proxmark_dump = build_proxmark3_dump(fd)

        return {
            "blocks": blocks,
            "hex": hex_dump,
            "proxmark3": proxmark_dump,
            "filament": fd.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/read")
async def read_tag(req: ReadTagRequest):
    """Request the NFC bridge phone to read a tag."""
    if not nfc_bridge.is_connected:
        raise HTTPException(status_code=503, detail="No phone connected to NFC bridge")
    try:
        result = await nfc_bridge.request_read(timeout=req.timeout)
        # Decode the tag data
        fd = parse_from_base64_blocks(result.get("blocks", []))
        return {
            "uid": result.get("uid", ""),
            "filament": fd.to_dict(),
            "blocks": result.get("blocks", []),
        }
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/write")
async def write_tag(req: WriteTagRequest):
    """Request the NFC bridge phone to write data to a tag."""
    if not nfc_bridge.is_connected:
        raise HTTPException(status_code=503, detail="No phone connected to NFC bridge")
    try:
        # Decode the first block to get the UID for key derivation
        first_block = base64.b64decode(req.blocks[0])
        uid = first_block[0:4]
        keys = derive_keys_from_hex(uid.hex())

        result = await nfc_bridge.request_write(
            keys=keys,
            blocks=req.blocks,
            uid=req.target_uid,
            timeout=30.0,
        )
        return result
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/read-and-save")
async def read_and_save(req: ReadTagRequest, db: Session = Depends(get_db)):
    """Read a tag via NFC bridge and save the dump to the database."""
    if not nfc_bridge.is_connected:
        raise HTTPException(status_code=503, detail="No phone connected to NFC bridge")
    try:
        result = await nfc_bridge.request_read(timeout=req.timeout)
        uid = result.get("uid", "")
        blocks = result.get("blocks", [])

        # Decode
        fd = parse_from_base64_blocks(blocks)

        # Save raw dump
        raw_data = b"".join(base64.b64decode(b) for b in blocks)
        dump = spool_service.save_tag_dump(db, uid=uid, raw_data=raw_data)

        return {
            "uid": uid,
            "filament": fd.to_dict(),
            "dump_id": dump.id,
        }
    except TimeoutError as e:
        raise HTTPException(status_code=408, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bridge/status")
async def bridge_status():
    """Check if the NFC bridge phone is connected."""
    return {"connected": nfc_bridge.is_connected}
