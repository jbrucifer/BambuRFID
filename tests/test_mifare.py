"""Tests for MIFARE Classic 1K structure helpers."""

import pytest
from backend.rfid.mifare import (
    sector_to_block, block_to_sector, is_sector_trailer,
    sector_trailer_block, data_blocks_for_sector, all_data_blocks,
    parse_sector_trailer, NUM_SECTORS, BLOCKS_PER_SECTOR,
    TOTAL_BLOCKS, TOTAL_BYTES,
)


class TestMifareConstants:
    def test_geometry(self):
        assert NUM_SECTORS == 16
        assert BLOCKS_PER_SECTOR == 4
        assert TOTAL_BLOCKS == 64
        assert TOTAL_BYTES == 1024


class TestBlockSectorMapping:
    def test_sector_to_block(self):
        assert sector_to_block(0) == 0
        assert sector_to_block(1) == 4
        assert sector_to_block(15) == 60

    def test_block_to_sector(self):
        assert block_to_sector(0) == 0
        assert block_to_sector(3) == 0
        assert block_to_sector(4) == 1
        assert block_to_sector(63) == 15

    def test_is_sector_trailer(self):
        # Sector trailers at blocks 3, 7, 11, ..., 63
        assert is_sector_trailer(3) is True
        assert is_sector_trailer(7) is True
        assert is_sector_trailer(63) is True
        # Non-trailers
        assert is_sector_trailer(0) is False
        assert is_sector_trailer(1) is False
        assert is_sector_trailer(4) is False

    def test_sector_trailer_block(self):
        assert sector_trailer_block(0) == 3
        assert sector_trailer_block(1) == 7
        assert sector_trailer_block(15) == 63

    def test_data_blocks_for_sector(self):
        assert data_blocks_for_sector(0) == [0, 1, 2]
        assert data_blocks_for_sector(1) == [4, 5, 6]
        assert data_blocks_for_sector(15) == [60, 61, 62]

    def test_all_data_blocks_count(self):
        blocks = all_data_blocks()
        # 16 sectors × 3 data blocks = 48
        assert len(blocks) == 48
        # None should be sector trailers
        for b in blocks:
            assert not is_sector_trailer(b)


class TestParseSectorTrailer:
    def test_valid_trailer(self):
        # Key A (6 bytes) + access bits (4 bytes) + Key B (6 bytes)
        data = bytes(range(16))
        result = parse_sector_trailer(data)
        assert result["key_a"] == bytes([0, 1, 2, 3, 4, 5])
        assert result["access_bits"] == bytes([6, 7, 8, 9])
        assert result["key_b"] == bytes([10, 11, 12, 13, 14, 15])

    def test_invalid_length_raises(self):
        with pytest.raises(ValueError):
            parse_sector_trailer(bytes(10))
