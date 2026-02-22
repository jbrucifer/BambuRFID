"""Tests for Bambu Lab tag format parsing and building."""

import struct
import pytest
from backend.rfid.bambu_format import (
    FilamentData, parse_tag_dump, build_tag_blocks,
    SECTOR_TRAILER_BLOCKS, RSA_DATA_BLOCKS,
)


def make_test_blocks() -> list[bytes]:
    """Create a synthetic 64-block tag dump with known values."""
    blocks = [bytearray(16) for _ in range(64)]

    # Block 0: UID + manufacturer data
    blocks[0][0:4] = bytes.fromhex("7AD43F1C")
    blocks[0][4:16] = b"\x88\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

    # Block 1: Material variant ID + Material ID
    blocks[1][0:8] = b"A50-K0\x00\x00"
    blocks[1][8:16] = b"GFA00\x00\x00\x00"

    # Block 2: Filament type (short)
    blocks[2][0:3] = b"PLA"

    # Block 4: Detailed filament type
    blocks[4][0:9] = b"PLA Basic"

    # Block 5: Color (RGBA) + weight + padding + diameter
    blocks[5][0:4] = bytes([0xFF, 0xFF, 0xFF, 0xFF])  # White
    blocks[5][4:6] = struct.pack("<H", 1000)  # 1000g
    blocks[5][8:12] = struct.pack("<f", 1.75)  # 1.75mm

    # Block 6: Temperatures
    blocks[6][0:2] = struct.pack("<H", 55)    # Drying temp
    blocks[6][2:4] = struct.pack("<H", 8)     # Drying time
    blocks[6][4:6] = struct.pack("<H", 1)     # Bed temp type
    blocks[6][6:8] = struct.pack("<H", 60)    # Bed temp
    blocks[6][8:10] = struct.pack("<H", 230)  # Max hotend
    blocks[6][10:12] = struct.pack("<H", 190) # Min hotend

    # Block 8: X Cam info + nozzle diameter
    blocks[8][12:16] = struct.pack("<f", 0.4)

    # Block 9: Tray UID
    blocks[9][0:8] = b"TRAY0001"

    # Block 10: Spool width (bytes 4-5, mm×100)
    blocks[10][4:6] = struct.pack("<H", 5600)  # 56.0mm

    # Block 12: Production datetime
    blocks[12][0:16] = b"2024_03_15_10_30"

    # Block 14: Filament length (bytes 4-5)
    blocks[14][4:6] = struct.pack("<H", 330)

    # Block 16: Color format
    blocks[16][0:2] = struct.pack("<H", 0)  # No secondary color

    return [bytes(b) for b in blocks]


class TestParseTagDump:
    def test_parse_uid(self):
        blocks = make_test_blocks()
        fd = parse_tag_dump(blocks)
        assert fd.uid == bytes.fromhex("7AD43F1C")

    def test_parse_material_ids(self):
        blocks = make_test_blocks()
        fd = parse_tag_dump(blocks)
        assert fd.material_variant_id == "A50-K0"
        assert fd.material_id == "GFA00"

    def test_parse_filament_type(self):
        blocks = make_test_blocks()
        fd = parse_tag_dump(blocks)
        assert fd.filament_type == "PLA"
        assert fd.detailed_filament_type == "PLA Basic"

    def test_parse_color(self):
        blocks = make_test_blocks()
        fd = parse_tag_dump(blocks)
        assert fd.color_rgba == bytes([0xFF, 0xFF, 0xFF, 0xFF])
        assert fd.color_hex == "#FFFFFF"

    def test_parse_weight(self):
        blocks = make_test_blocks()
        fd = parse_tag_dump(blocks)
        assert fd.spool_weight_g == 1000

    def test_parse_diameter(self):
        blocks = make_test_blocks()
        fd = parse_tag_dump(blocks)
        assert abs(fd.filament_diameter_mm - 1.75) < 0.01

    def test_parse_temperatures(self):
        blocks = make_test_blocks()
        fd = parse_tag_dump(blocks)
        assert fd.drying_temp_c == 55
        assert fd.drying_time_h == 8
        assert fd.bed_temp_c == 60
        assert fd.max_hotend_temp_c == 230
        assert fd.min_hotend_temp_c == 190

    def test_parse_nozzle_diameter(self):
        blocks = make_test_blocks()
        fd = parse_tag_dump(blocks)
        assert abs(fd.nozzle_diameter - 0.4) < 0.01

    def test_parse_tray_uid(self):
        blocks = make_test_blocks()
        fd = parse_tag_dump(blocks)
        assert fd.tray_uid == "TRAY0001"

    def test_parse_spool_width(self):
        blocks = make_test_blocks()
        fd = parse_tag_dump(blocks)
        assert abs(fd.spool_width_mm - 56.0) < 0.01

    def test_parse_production_datetime(self):
        blocks = make_test_blocks()
        fd = parse_tag_dump(blocks)
        assert fd.production_datetime == "2024_03_15_10_30"

    def test_parse_filament_length(self):
        blocks = make_test_blocks()
        fd = parse_tag_dump(blocks)
        assert fd.filament_length_m == 330

    def test_wrong_block_count_raises(self):
        with pytest.raises(ValueError):
            parse_tag_dump([bytes(16)] * 32)

    def test_wrong_block_size_raises(self):
        blocks = [bytes(16)] * 63 + [bytes(8)]
        with pytest.raises(ValueError):
            parse_tag_dump(blocks)


class TestBuildTagBlocks:
    def test_roundtrip(self):
        """Parse → build → parse should preserve all data."""
        original_blocks = make_test_blocks()
        fd = parse_tag_dump(original_blocks)
        rebuilt_blocks = build_tag_blocks(fd)
        fd2 = parse_tag_dump(rebuilt_blocks)

        assert fd2.uid == fd.uid
        assert fd2.material_variant_id == fd.material_variant_id
        assert fd2.material_id == fd.material_id
        assert fd2.filament_type == fd.filament_type
        assert fd2.detailed_filament_type == fd.detailed_filament_type
        assert fd2.color_rgba == fd.color_rgba
        assert fd2.spool_weight_g == fd.spool_weight_g
        assert abs(fd2.filament_diameter_mm - fd.filament_diameter_mm) < 0.01
        assert fd2.max_hotend_temp_c == fd.max_hotend_temp_c
        assert fd2.min_hotend_temp_c == fd.min_hotend_temp_c
        assert fd2.bed_temp_c == fd.bed_temp_c
        assert fd2.filament_length_m == fd.filament_length_m

    def test_build_produces_64_blocks(self):
        fd = FilamentData()
        blocks = build_tag_blocks(fd)
        assert len(blocks) == 64

    def test_each_block_is_16_bytes(self):
        fd = FilamentData()
        blocks = build_tag_blocks(fd)
        for i, b in enumerate(blocks):
            assert len(b) == 16, f"Block {i} is {len(b)} bytes"

    def test_build_with_custom_values(self):
        fd = FilamentData()
        fd.filament_type = "PETG"
        fd.detailed_filament_type = "PETG Basic"
        fd.color_rgba = bytes([0xFF, 0x00, 0x00, 0xFF])  # Red
        fd.spool_weight_g = 750
        fd.max_hotend_temp_c = 260
        fd.min_hotend_temp_c = 220

        blocks = build_tag_blocks(fd)
        fd2 = parse_tag_dump(blocks)

        assert fd2.filament_type == "PETG"
        assert fd2.detailed_filament_type == "PETG Basic"
        assert fd2.color_hex == "#FF0000"
        assert fd2.spool_weight_g == 750
        assert fd2.max_hotend_temp_c == 260
        assert fd2.min_hotend_temp_c == 220


class TestFilamentDataDict:
    def test_to_dict(self):
        blocks = make_test_blocks()
        fd = parse_tag_dump(blocks)
        d = fd.to_dict()

        assert d["uid"] == "7AD43F1C"
        assert d["material_id"] == "GFA00"
        assert d["color_hex"] == "#FFFFFF"
        assert d["spool_weight_g"] == 1000
        assert d["max_hotend_temp_c"] == 230
        assert d["min_hotend_temp_c"] == 190
        assert d["has_rsa_signature"] is False  # Test blocks have no signature
