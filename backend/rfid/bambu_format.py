"""
Bambu Lab RFID tag data format — block layout and field definitions.

Based on community reverse-engineering from:
https://github.com/Bambu-Research-Group/RFID-Tag-Guide/blob/main/BambuLabRfid.md

MIFARE Classic 1K: 16 sectors × 4 blocks × 16 bytes = 1024 bytes total.
Every 4th block (3, 7, 11, ...) is a sector trailer (keys + access bits).

All multi-byte numeric values are Little Endian (LE).
"""

import struct
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ──────────────────────────────────────────────
# Known Bambu Lab material type strings
# ──────────────────────────────────────────────

class MaterialType(str, Enum):
    PLA_BASIC = "PLA Basic"
    PLA_MATTE = "PLA Matte"
    PLA_SILK = "PLA Silk"
    PLA_METAL = "PLA Metal"
    PLA_SPARKLE = "PLA Sparkle"
    PLA_CF = "PLA-CF"
    PLA_AERO = "PLA Aero"
    PETG_BASIC = "PETG Basic"
    PETG_CF = "PETG-CF"
    PETG_HF = "PETG HF"
    ABS = "ABS"
    ASA = "ASA"
    TPU_95A = "TPU 95A"
    PA6_CF = "PA6-CF"
    PA6_GF = "PA6-GF"
    PVA = "PVA"
    SUPPORT_W = "Support W"
    SUPPORT_G = "Support G"
    PC = "PC"
    HIPS = "HIPS"
    PPA_CF = "PPA-CF"
    PPA_GF = "PPA-GF"


# ──────────────────────────────────────────────
# Filament data model
# ──────────────────────────────────────────────

@dataclass
class FilamentData:
    """Decoded filament data from a Bambu Lab RFID tag."""

    # Sector 0
    uid: bytes = b""
    manufacturer_data: bytes = b""
    material_variant_id: str = ""       # e.g. "A50-K0"
    material_id: str = ""               # e.g. "GFA00"

    # Sector 0, Block 2 + Sector 1, Block 4
    filament_type: str = ""             # Short type, e.g. "PLA"
    detailed_filament_type: str = ""    # Full name, e.g. "PLA Basic"

    # Sector 1, Block 5
    color_rgba: bytes = b"\x00\x00\x00\xFF"  # 4 bytes: R, G, B, A
    spool_weight_g: int = 0             # Spool net weight in grams
    filament_diameter_mm: float = 1.75  # Filament diameter

    # Sector 1, Block 6
    drying_temp_c: int = 0
    drying_time_h: int = 0
    bed_temp_type: int = 0
    bed_temp_c: int = 0
    max_hotend_temp_c: int = 0
    min_hotend_temp_c: int = 0

    # Sector 2, Block 8
    xcam_info: bytes = b""
    nozzle_diameter: float = 0.0

    # Sector 2, Block 9
    tray_uid: str = ""

    # Sector 2, Block 10
    spool_width_mm: float = 0.0        # Stored as mm×100

    # Sector 3, Block 12-13
    production_datetime: str = ""       # e.g. "2024_03_15_10_30"
    short_production_datetime: str = ""

    # Sector 3, Block 14
    filament_length_m: int = 0          # Filament length in meters

    # Sector 4, Block 16-17 (multi-color info)
    color_format: int = 0               # 0x0000 = empty, 0x0002 = has secondary color
    color_count: int = 0
    secondary_color_abgr: bytes = b""

    # Sectors 10-15: RSA-2048 signature (256 bytes)
    rsa_signature: bytes = b""

    # Raw block data for cloning
    raw_blocks: list[bytes] = field(default_factory=list)

    @property
    def color_hex(self) -> str:
        """Return color as #RRGGBB hex string."""
        if len(self.color_rgba) >= 3:
            return "#{:02X}{:02X}{:02X}".format(
                self.color_rgba[0], self.color_rgba[1], self.color_rgba[2]
            )
        return "#000000"

    @property
    def color_alpha(self) -> int:
        """Return the alpha channel (0-255)."""
        if len(self.color_rgba) >= 4:
            return self.color_rgba[3]
        return 255

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "uid": self.uid.hex().upper() if self.uid else "",
            "material_variant_id": self.material_variant_id,
            "material_id": self.material_id,
            "filament_type": self.filament_type,
            "detailed_filament_type": self.detailed_filament_type,
            "color_hex": self.color_hex,
            "color_alpha": self.color_alpha,
            "spool_weight_g": self.spool_weight_g,
            "filament_diameter_mm": round(self.filament_diameter_mm, 2),
            "drying_temp_c": self.drying_temp_c,
            "drying_time_h": self.drying_time_h,
            "bed_temp_type": self.bed_temp_type,
            "bed_temp_c": self.bed_temp_c,
            "max_hotend_temp_c": self.max_hotend_temp_c,
            "min_hotend_temp_c": self.min_hotend_temp_c,
            "nozzle_diameter": round(self.nozzle_diameter, 2),
            "tray_uid": self.tray_uid,
            "spool_width_mm": round(self.spool_width_mm, 2),
            "production_datetime": self.production_datetime,
            "filament_length_m": self.filament_length_m,
            "color_format": self.color_format,
            "color_count": self.color_count,
            "has_rsa_signature": len(self.rsa_signature) > 0 and any(b != 0 for b in self.rsa_signature),
        }


# ──────────────────────────────────────────────
# Block layout definitions
# ──────────────────────────────────────────────

# Sector trailer blocks (contain MIFARE keys, not Bambu data)
SECTOR_TRAILER_BLOCKS = {3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51, 55, 59, 63}

# RSA signature is stored across sectors 10-15 (blocks 40-63, excluding trailers)
# That's 6 sectors × 3 data blocks × 16 bytes = 288 bytes, but RSA-2048 = 256 bytes
RSA_SIGNATURE_SECTORS = range(10, 16)
RSA_DATA_BLOCKS = []
for _s in RSA_SIGNATURE_SECTORS:
    for _i in range(3):  # 3 data blocks per sector
        RSA_DATA_BLOCKS.append(_s * 4 + _i)

# Empty sectors (5-9) — no data stored
EMPTY_SECTORS = range(5, 10)


def _read_string(block_data: bytes, start: int = 0, length: Optional[int] = None) -> str:
    """Read a null-terminated ASCII string from block data."""
    if length is None:
        length = len(block_data) - start
    raw = block_data[start:start + length]
    # Strip null bytes and trailing whitespace
    return raw.split(b"\x00")[0].decode("ascii", errors="replace").strip()


def _read_uint16_le(data: bytes, offset: int) -> int:
    """Read a uint16 little-endian value."""
    return struct.unpack_from("<H", data, offset)[0]


def _read_float_le(data: bytes, offset: int) -> float:
    """Read a 32-bit float little-endian value."""
    return struct.unpack_from("<f", data, offset)[0]


def _write_uint16_le(value: int) -> bytes:
    """Write a uint16 little-endian value."""
    return struct.pack("<H", value)


def _write_float_le(value: float) -> bytes:
    """Write a 32-bit float little-endian value."""
    return struct.pack("<f", value)


def parse_tag_dump(blocks: list[bytes]) -> FilamentData:
    """
    Parse a complete MIFARE Classic 1K tag dump into FilamentData.

    Args:
        blocks: List of 64 blocks, each 16 bytes.

    Returns:
        Parsed FilamentData object.
    """
    if len(blocks) != 64:
        raise ValueError(f"Expected 64 blocks, got {len(blocks)}")
    for i, b in enumerate(blocks):
        if len(b) != 16:
            raise ValueError(f"Block {i} must be 16 bytes, got {len(b)}")

    fd = FilamentData()
    fd.raw_blocks = list(blocks)

    # ── Sector 0 ──
    # Block 0: UID + manufacturer data
    fd.uid = blocks[0][0:4]
    fd.manufacturer_data = blocks[0][4:16]

    # Block 1: Material variant ID (bytes 0-7) + Material ID (bytes 8-15)
    fd.material_variant_id = _read_string(blocks[1], 0, 8)
    fd.material_id = _read_string(blocks[1], 8, 8)

    # Block 2: Filament type (short)
    fd.filament_type = _read_string(blocks[2], 0, 16)

    # ── Sector 1 ──
    # Block 4: Detailed filament type
    fd.detailed_filament_type = _read_string(blocks[4], 0, 16)

    # Block 5: Color (RGBA) + spool weight + filament diameter
    fd.color_rgba = bytes(blocks[5][0:4])
    fd.spool_weight_g = _read_uint16_le(blocks[5], 4)
    fd.filament_diameter_mm = _read_float_le(blocks[5], 8)

    # Block 6: Temperatures
    fd.drying_temp_c = _read_uint16_le(blocks[6], 0)
    fd.drying_time_h = _read_uint16_le(blocks[6], 2)
    fd.bed_temp_type = _read_uint16_le(blocks[6], 4)
    fd.bed_temp_c = _read_uint16_le(blocks[6], 6)
    fd.max_hotend_temp_c = _read_uint16_le(blocks[6], 8)
    fd.min_hotend_temp_c = _read_uint16_le(blocks[6], 10)

    # ── Sector 2 ──
    # Block 8: X Cam info + nozzle diameter
    fd.xcam_info = bytes(blocks[8][0:12])
    fd.nozzle_diameter = _read_float_le(blocks[8], 12)

    # Block 9: Tray UID
    fd.tray_uid = _read_string(blocks[9], 0, 16)

    # Block 10: Spool width (bytes 4-5, stored as mm×100)
    raw_width = _read_uint16_le(blocks[10], 4)
    fd.spool_width_mm = raw_width / 100.0

    # ── Sector 3 ──
    # Block 12: Production datetime
    fd.production_datetime = _read_string(blocks[12], 0, 16)

    # Block 13: Short production datetime
    fd.short_production_datetime = _read_string(blocks[13], 0, 16)

    # Block 14: Filament length in meters (bytes 4-5)
    fd.filament_length_m = _read_uint16_le(blocks[14], 4)

    # ── Sector 4 ──
    # Block 16: Multi-color info
    fd.color_format = _read_uint16_le(blocks[16], 0)
    fd.color_count = _read_uint16_le(blocks[16], 2)
    if fd.color_format == 2 and len(blocks[16]) >= 8:
        fd.secondary_color_abgr = bytes(blocks[16][4:8])

    # ── Sectors 10-15: RSA Signature ──
    sig_bytes = bytearray()
    for blk_num in RSA_DATA_BLOCKS:
        sig_bytes.extend(blocks[blk_num])
    fd.rsa_signature = bytes(sig_bytes[:256])  # RSA-2048 = 256 bytes

    return fd


def build_tag_blocks(fd: FilamentData) -> list[bytes]:
    """
    Build a complete 64-block MIFARE Classic 1K tag dump from FilamentData.

    If raw_blocks are present (from a cloned tag), those are used as the base
    and only modified fields are overwritten. Otherwise, blocks are built
    from scratch.

    Args:
        fd: FilamentData to encode.

    Returns:
        List of 64 blocks, each 16 bytes.
    """
    # Start from raw blocks if available (clone mode), otherwise zeroed
    if fd.raw_blocks and len(fd.raw_blocks) == 64:
        blocks = [bytearray(b) for b in fd.raw_blocks]
    else:
        blocks = [bytearray(16) for _ in range(64)]

    # ── Sector 0 ──
    # Block 0: UID + manufacturer data (read-only on real tags, writable on magic tags)
    if fd.uid:
        blocks[0][0:4] = fd.uid[:4].ljust(4, b"\x00")
    if fd.manufacturer_data:
        blocks[0][4:16] = fd.manufacturer_data[:12].ljust(12, b"\x00")

    # Block 1: Material variant ID + Material ID
    blocks[1][0:8] = fd.material_variant_id.encode("ascii")[:8].ljust(8, b"\x00")
    blocks[1][8:16] = fd.material_id.encode("ascii")[:8].ljust(8, b"\x00")

    # Block 2: Filament type (short)
    blocks[2][0:16] = fd.filament_type.encode("ascii")[:16].ljust(16, b"\x00")

    # ── Sector 1 ──
    # Block 4: Detailed filament type
    blocks[4][0:16] = fd.detailed_filament_type.encode("ascii")[:16].ljust(16, b"\x00")

    # Block 5: Color + spool weight + padding + diameter
    blocks[5][0:4] = fd.color_rgba[:4]
    blocks[5][4:6] = _write_uint16_le(fd.spool_weight_g)
    # bytes 6-7: padding (leave as-is or zero)
    blocks[5][8:12] = _write_float_le(fd.filament_diameter_mm)

    # Block 6: Temperatures
    blocks[6][0:2] = _write_uint16_le(fd.drying_temp_c)
    blocks[6][2:4] = _write_uint16_le(fd.drying_time_h)
    blocks[6][4:6] = _write_uint16_le(fd.bed_temp_type)
    blocks[6][6:8] = _write_uint16_le(fd.bed_temp_c)
    blocks[6][8:10] = _write_uint16_le(fd.max_hotend_temp_c)
    blocks[6][10:12] = _write_uint16_le(fd.min_hotend_temp_c)

    # ── Sector 2 ──
    # Block 8: X Cam info + nozzle diameter
    if fd.xcam_info:
        blocks[8][0:12] = fd.xcam_info[:12].ljust(12, b"\x00")
    blocks[8][12:16] = _write_float_le(fd.nozzle_diameter)

    # Block 9: Tray UID
    blocks[9][0:16] = fd.tray_uid.encode("ascii")[:16].ljust(16, b"\x00")

    # Block 10: Spool width (bytes 4-5 as mm×100)
    raw_width = int(fd.spool_width_mm * 100)
    blocks[10][4:6] = _write_uint16_le(raw_width)

    # ── Sector 3 ──
    # Block 12: Production datetime
    blocks[12][0:16] = fd.production_datetime.encode("ascii")[:16].ljust(16, b"\x00")

    # Block 13: Short production datetime
    blocks[13][0:16] = fd.short_production_datetime.encode("ascii")[:16].ljust(16, b"\x00")

    # Block 14: Filament length (bytes 4-5)
    blocks[14][4:6] = _write_uint16_le(fd.filament_length_m)

    # ── Sector 4 ──
    # Block 16: Multi-color info
    blocks[16][0:2] = _write_uint16_le(fd.color_format)
    blocks[16][2:4] = _write_uint16_le(fd.color_count)
    if fd.secondary_color_abgr:
        blocks[16][4:8] = fd.secondary_color_abgr[:4]

    # ── Sectors 10-15: RSA Signature ──
    if fd.rsa_signature:
        sig = fd.rsa_signature[:256].ljust(256, b"\x00")
        offset = 0
        for blk_num in RSA_DATA_BLOCKS:
            chunk = sig[offset:offset + 16]
            if len(chunk) == 16:
                blocks[blk_num] = bytearray(chunk)
            offset += 16

    return [bytes(b) for b in blocks]
