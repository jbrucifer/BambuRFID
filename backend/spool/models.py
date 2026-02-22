"""SQLAlchemy models for spool inventory and filament management."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, LargeBinary, ForeignKey, Text
from sqlalchemy.orm import relationship

from .database import Base


class Spool(Base):
    """A filament spool tracked in the inventory."""
    __tablename__ = "spools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    brand = Column(String(100), default="")
    material = Column(String(50), nullable=False)          # e.g. "PLA Basic"
    material_id = Column(String(20), default="")           # Bambu material ID e.g. "GFA00"
    color_hex = Column(String(7), default="#000000")       # #RRGGBB
    color_name = Column(String(50), default="")
    weight_g = Column(Integer, default=1000)               # Net weight in grams
    remaining_g = Column(Integer, default=1000)            # Estimated remaining
    filament_length_m = Column(Integer, default=0)
    diameter_mm = Column(Float, default=1.75)
    nozzle_temp_min = Column(Integer, default=190)
    nozzle_temp_max = Column(Integer, default=230)
    bed_temp = Column(Integer, default=60)
    drying_temp = Column(Integer, default=0)
    drying_time_h = Column(Integer, default=0)
    tag_uid = Column(String(20), default="")               # RFID tag UID if scanned
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    # Relationship to tag dumps
    tag_dumps = relationship("TagDump", back_populates="spool", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "material": self.material,
            "material_id": self.material_id,
            "color_hex": self.color_hex,
            "color_name": self.color_name,
            "weight_g": self.weight_g,
            "remaining_g": self.remaining_g,
            "filament_length_m": self.filament_length_m,
            "diameter_mm": self.diameter_mm,
            "nozzle_temp_min": self.nozzle_temp_min,
            "nozzle_temp_max": self.nozzle_temp_max,
            "bed_temp": self.bed_temp,
            "drying_temp": self.drying_temp,
            "drying_time_h": self.drying_time_h,
            "tag_uid": self.tag_uid,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }


class TagDump(Base):
    """Raw RFID tag dump associated with a spool."""
    __tablename__ = "tag_dumps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    spool_id = Column(Integer, ForeignKey("spools.id"), nullable=True)
    uid = Column(String(20), nullable=False)
    raw_data = Column(LargeBinary, nullable=False)  # Full 1024-byte dump
    source = Column(String(50), default="nfc_bridge")  # nfc_bridge, file_upload, proxmark3
    dumped_at = Column(DateTime, default=datetime.utcnow)

    spool = relationship("Spool", back_populates="tag_dumps")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "spool_id": self.spool_id,
            "uid": self.uid,
            "source": self.source,
            "dumped_at": self.dumped_at.isoformat() if self.dumped_at else None,
            "data_size": len(self.raw_data) if self.raw_data else 0,
        }


class MaterialPreset(Base):
    """Pre-defined filament material profiles."""
    __tablename__ = "material_presets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)    # "PLA Basic"
    material_type = Column(String(30), nullable=False)         # "PLA"
    material_id = Column(String(20), default="")               # Bambu code
    material_variant_id = Column(String(20), default="")
    nozzle_temp_min = Column(Integer, nullable=False)
    nozzle_temp_max = Column(Integer, nullable=False)
    bed_temp = Column(Integer, default=60)
    bed_temp_type = Column(Integer, default=0)
    drying_temp = Column(Integer, default=0)
    drying_time_h = Column(Integer, default=0)
    density = Column(Float, default=1.24)                      # g/cm³
    diameter_mm = Column(Float, default=1.75)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "material_type": self.material_type,
            "material_id": self.material_id,
            "material_variant_id": self.material_variant_id,
            "nozzle_temp_min": self.nozzle_temp_min,
            "nozzle_temp_max": self.nozzle_temp_max,
            "bed_temp": self.bed_temp,
            "bed_temp_type": self.bed_temp_type,
            "drying_temp": self.drying_temp,
            "drying_time_h": self.drying_time_h,
            "density": self.density,
            "diameter_mm": self.diameter_mm,
        }


class PrinterConfig(Base):
    """Saved printer MQTT connection configurations."""
    __tablename__ = "printer_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    ip_address = Column(String(45), nullable=False)
    serial_number = Column(String(50), nullable=False)
    access_code = Column(String(20), nullable=False)
    model = Column(String(50), default="")  # X1C, P1S, A1, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "ip_address": self.ip_address,
            "serial_number": self.serial_number,
            "access_code": "****",  # Never expose in API
            "model": self.model,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
