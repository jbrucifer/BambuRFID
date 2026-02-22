"""API routes for spool inventory management."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.spool.database import get_db
from backend.spool import service

router = APIRouter(prefix="/api/spools", tags=["spools"])


class SpoolCreate(BaseModel):
    name: str
    brand: str = ""
    material: str
    material_id: str = ""
    color_hex: str = "#000000"
    color_name: str = ""
    weight_g: int = 1000
    remaining_g: int = 1000
    filament_length_m: int = 0
    diameter_mm: float = 1.75
    nozzle_temp_min: int = 190
    nozzle_temp_max: int = 230
    bed_temp: int = 60
    drying_temp: int = 0
    drying_time_h: int = 0
    tag_uid: str = ""
    notes: str = ""


class SpoolUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    material: Optional[str] = None
    material_id: Optional[str] = None
    color_hex: Optional[str] = None
    color_name: Optional[str] = None
    weight_g: Optional[int] = None
    remaining_g: Optional[int] = None
    filament_length_m: Optional[int] = None
    diameter_mm: Optional[float] = None
    nozzle_temp_min: Optional[int] = None
    nozzle_temp_max: Optional[int] = None
    bed_temp: Optional[int] = None
    drying_temp: Optional[int] = None
    drying_time_h: Optional[int] = None
    tag_uid: Optional[str] = None
    notes: Optional[str] = None


@router.get("/")
async def list_spools(db: Session = Depends(get_db)):
    """List all spools in the inventory."""
    spools = service.get_all_spools(db)
    return {"spools": [s.to_dict() for s in spools]}


@router.get("/{spool_id}")
async def get_spool(spool_id: int, db: Session = Depends(get_db)):
    """Get a single spool by ID."""
    spool = service.get_spool(db, spool_id)
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")
    return spool.to_dict()


@router.post("/")
async def create_spool(data: SpoolCreate, db: Session = Depends(get_db)):
    """Create a new spool."""
    spool = service.create_spool(db, data.model_dump())
    return spool.to_dict()


@router.put("/{spool_id}")
async def update_spool(spool_id: int, data: SpoolUpdate, db: Session = Depends(get_db)):
    """Update a spool."""
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    spool = service.update_spool(db, spool_id, update_data)
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")
    return spool.to_dict()


@router.delete("/{spool_id}")
async def delete_spool(spool_id: int, db: Session = Depends(get_db)):
    """Delete a spool."""
    if not service.delete_spool(db, spool_id):
        raise HTTPException(status_code=404, detail="Spool not found")
    return {"deleted": True}


@router.post("/{spool_id}/touch")
async def touch_spool(spool_id: int, db: Session = Depends(get_db)):
    """Mark a spool as recently used."""
    spool = service.touch_spool(db, spool_id)
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")
    return spool.to_dict()


# ──────────────────────────────────────────────
# Tag dumps
# ──────────────────────────────────────────────

@router.get("/{spool_id}/dumps")
async def list_dumps(spool_id: int, db: Session = Depends(get_db)):
    """List tag dumps for a spool."""
    dumps = service.get_tag_dumps(db, spool_id=spool_id)
    return {"dumps": [d.to_dict() for d in dumps]}


@router.get("/dumps/all")
async def list_all_dumps(db: Session = Depends(get_db)):
    """List all tag dumps."""
    dumps = service.get_tag_dumps(db)
    return {"dumps": [d.to_dict() for d in dumps]}


# ──────────────────────────────────────────────
# Material presets
# ──────────────────────────────────────────────

@router.get("/presets/all")
async def list_presets(db: Session = Depends(get_db)):
    """List all material presets."""
    presets = service.get_all_presets(db)
    return {"presets": [p.to_dict() for p in presets]}


@router.get("/presets/{preset_id}")
async def get_preset(preset_id: int, db: Session = Depends(get_db)):
    """Get a single material preset."""
    preset = service.get_preset(db, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
    return preset.to_dict()
