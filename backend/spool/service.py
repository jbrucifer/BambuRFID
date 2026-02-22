"""Spool CRUD operations and material preset management."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .models import Spool, TagDump, MaterialPreset, PrinterConfig


# ──────────────────────────────────────────────
# Spool operations
# ──────────────────────────────────────────────

def get_all_spools(db: Session) -> list[Spool]:
    return db.query(Spool).order_by(Spool.last_used_at.desc().nullslast()).all()


def get_spool(db: Session, spool_id: int) -> Optional[Spool]:
    return db.query(Spool).filter(Spool.id == spool_id).first()


def create_spool(db: Session, data: dict) -> Spool:
    spool = Spool(**data)
    db.add(spool)
    db.commit()
    db.refresh(spool)
    return spool


def update_spool(db: Session, spool_id: int, data: dict) -> Optional[Spool]:
    spool = get_spool(db, spool_id)
    if not spool:
        return None
    for key, value in data.items():
        if hasattr(spool, key):
            setattr(spool, key, value)
    db.commit()
    db.refresh(spool)
    return spool


def delete_spool(db: Session, spool_id: int) -> bool:
    spool = get_spool(db, spool_id)
    if not spool:
        return False
    db.delete(spool)
    db.commit()
    return True


def touch_spool(db: Session, spool_id: int) -> Optional[Spool]:
    """Update the last_used_at timestamp."""
    return update_spool(db, spool_id, {"last_used_at": datetime.utcnow()})


# ──────────────────────────────────────────────
# Tag dump operations
# ──────────────────────────────────────────────

def save_tag_dump(db: Session, uid: str, raw_data: bytes,
                  spool_id: Optional[int] = None, source: str = "nfc_bridge") -> TagDump:
    dump = TagDump(uid=uid, raw_data=raw_data, spool_id=spool_id, source=source)
    db.add(dump)
    db.commit()
    db.refresh(dump)
    return dump


def get_tag_dumps(db: Session, spool_id: Optional[int] = None) -> list[TagDump]:
    query = db.query(TagDump)
    if spool_id is not None:
        query = query.filter(TagDump.spool_id == spool_id)
    return query.order_by(TagDump.dumped_at.desc()).all()


def get_tag_dump(db: Session, dump_id: int) -> Optional[TagDump]:
    return db.query(TagDump).filter(TagDump.id == dump_id).first()


# ──────────────────────────────────────────────
# Material preset operations
# ──────────────────────────────────────────────

def get_all_presets(db: Session) -> list[MaterialPreset]:
    return db.query(MaterialPreset).order_by(MaterialPreset.name).all()


def get_preset(db: Session, preset_id: int) -> Optional[MaterialPreset]:
    return db.query(MaterialPreset).filter(MaterialPreset.id == preset_id).first()


def get_preset_by_name(db: Session, name: str) -> Optional[MaterialPreset]:
    return db.query(MaterialPreset).filter(MaterialPreset.name == name).first()


def seed_default_presets(db: Session):
    """Insert default material presets if the table is empty."""
    if db.query(MaterialPreset).count() > 0:
        return

    defaults = [
        MaterialPreset(name="PLA Basic", material_type="PLA", material_id="GFA00",
                       nozzle_temp_min=190, nozzle_temp_max=230, bed_temp=60,
                       drying_temp=55, drying_time_h=8, density=1.24),
        MaterialPreset(name="PLA Matte", material_type="PLA", material_id="GFA01",
                       nozzle_temp_min=190, nozzle_temp_max=230, bed_temp=60,
                       drying_temp=55, drying_time_h=8, density=1.24),
        MaterialPreset(name="PLA Silk", material_type="PLA", material_id="GFA02",
                       nozzle_temp_min=200, nozzle_temp_max=230, bed_temp=60,
                       drying_temp=55, drying_time_h=8, density=1.24),
        MaterialPreset(name="PLA-CF", material_type="PLA", material_id="GFA50",
                       nozzle_temp_min=220, nozzle_temp_max=260, bed_temp=60,
                       drying_temp=55, drying_time_h=8, density=1.29),
        MaterialPreset(name="PETG Basic", material_type="PETG", material_id="GFB00",
                       nozzle_temp_min=220, nozzle_temp_max=260, bed_temp=70,
                       drying_temp=65, drying_time_h=8, density=1.27),
        MaterialPreset(name="PETG HF", material_type="PETG", material_id="GFB01",
                       nozzle_temp_min=230, nozzle_temp_max=260, bed_temp=70,
                       drying_temp=65, drying_time_h=8, density=1.27),
        MaterialPreset(name="PETG-CF", material_type="PETG", material_id="GFB50",
                       nozzle_temp_min=240, nozzle_temp_max=270, bed_temp=70,
                       drying_temp=65, drying_time_h=8, density=1.30),
        MaterialPreset(name="ABS", material_type="ABS", material_id="GFC00",
                       nozzle_temp_min=240, nozzle_temp_max=270, bed_temp=100,
                       drying_temp=80, drying_time_h=8, density=1.04),
        MaterialPreset(name="ASA", material_type="ASA", material_id="GFD00",
                       nozzle_temp_min=240, nozzle_temp_max=270, bed_temp=100,
                       drying_temp=80, drying_time_h=8, density=1.07),
        MaterialPreset(name="TPU 95A", material_type="TPU", material_id="GFE00",
                       nozzle_temp_min=200, nozzle_temp_max=230, bed_temp=60,
                       drying_temp=55, drying_time_h=8, density=1.21),
        MaterialPreset(name="PA6-CF", material_type="PA", material_id="GFN03",
                       nozzle_temp_min=270, nozzle_temp_max=300, bed_temp=100,
                       drying_temp=80, drying_time_h=12, density=1.18),
        MaterialPreset(name="PA6-GF", material_type="PA", material_id="GFN04",
                       nozzle_temp_min=270, nozzle_temp_max=300, bed_temp=100,
                       drying_temp=80, drying_time_h=12, density=1.36),
        MaterialPreset(name="PVA", material_type="PVA", material_id="GFS00",
                       nozzle_temp_min=190, nozzle_temp_max=210, bed_temp=60,
                       drying_temp=55, drying_time_h=8, density=1.19),
        MaterialPreset(name="Support W", material_type="Support", material_id="GFS01",
                       nozzle_temp_min=190, nozzle_temp_max=230, bed_temp=60,
                       drying_temp=55, drying_time_h=8, density=1.24),
        MaterialPreset(name="Support G", material_type="Support", material_id="GFS02",
                       nozzle_temp_min=190, nozzle_temp_max=230, bed_temp=60,
                       drying_temp=55, drying_time_h=8, density=1.24),
        MaterialPreset(name="PC", material_type="PC", material_id="GFG00",
                       nozzle_temp_min=260, nozzle_temp_max=290, bed_temp=110,
                       drying_temp=80, drying_time_h=12, density=1.20),
        MaterialPreset(name="HIPS", material_type="HIPS", material_id="GFH00",
                       nozzle_temp_min=220, nozzle_temp_max=250, bed_temp=90,
                       drying_temp=65, drying_time_h=8, density=1.04),
    ]
    db.add_all(defaults)
    db.commit()


# ──────────────────────────────────────────────
# Printer config operations
# ──────────────────────────────────────────────

def get_all_printers(db: Session) -> list[PrinterConfig]:
    return db.query(PrinterConfig).order_by(PrinterConfig.name).all()


def get_printer(db: Session, printer_id: int) -> Optional[PrinterConfig]:
    return db.query(PrinterConfig).filter(PrinterConfig.id == printer_id).first()


def create_printer(db: Session, data: dict) -> PrinterConfig:
    printer = PrinterConfig(**data)
    db.add(printer)
    db.commit()
    db.refresh(printer)
    return printer


def delete_printer(db: Session, printer_id: int) -> bool:
    printer = get_printer(db, printer_id)
    if not printer:
        return False
    db.delete(printer)
    db.commit()
    return True
