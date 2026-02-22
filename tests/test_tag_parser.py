"""Tests for high-level tag parser functions."""

import base64
import pytest
from backend.rfid.tag_parser import (
    parse_from_binary, parse_from_hex, parse_from_base64,
    parse_from_base64_blocks, parse_from_hex_blocks,
    parse_proxmark3_dump,
)
from backend.rfid.mifare import TOTAL_BYTES, TOTAL_BLOCKS, BYTES_PER_BLOCK


def make_binary_dump() -> bytes:
    """Create a minimal 1024-byte dump."""
    data = bytearray(TOTAL_BYTES)
    # Set some UID bytes
    data[0:4] = bytes.fromhex("DEADBEEF")
    return bytes(data)


class TestParseFromBinary:
    def test_valid_binary(self):
        data = make_binary_dump()
        fd = parse_from_binary(data)
        assert fd.uid == bytes.fromhex("DEADBEEF")

    def test_wrong_size_raises(self):
        with pytest.raises(ValueError):
            parse_from_binary(bytes(512))


class TestParseFromHex:
    def test_valid_hex(self):
        data = make_binary_dump()
        hex_str = data.hex()
        fd = parse_from_hex(hex_str)
        assert fd.uid == bytes.fromhex("DEADBEEF")

    def test_hex_with_spaces(self):
        data = make_binary_dump()
        # Insert spaces every 2 chars
        hex_str = " ".join(data.hex()[i:i+2] for i in range(0, len(data.hex()), 2))
        fd = parse_from_hex(hex_str)
        assert fd.uid == bytes.fromhex("DEADBEEF")


class TestParseFromBase64:
    def test_valid_base64(self):
        data = make_binary_dump()
        b64 = base64.b64encode(data).decode()
        fd = parse_from_base64(b64)
        assert fd.uid == bytes.fromhex("DEADBEEF")


class TestParseFromBase64Blocks:
    def test_valid_blocks(self):
        data = make_binary_dump()
        blocks = []
        for i in range(TOTAL_BLOCKS):
            block = data[i * BYTES_PER_BLOCK:(i + 1) * BYTES_PER_BLOCK]
            blocks.append(base64.b64encode(block).decode())
        fd = parse_from_base64_blocks(blocks)
        assert fd.uid == bytes.fromhex("DEADBEEF")


class TestParseFromHexBlocks:
    def test_valid_hex_blocks(self):
        data = make_binary_dump()
        blocks = []
        for i in range(TOTAL_BLOCKS):
            block = data[i * BYTES_PER_BLOCK:(i + 1) * BYTES_PER_BLOCK]
            blocks.append(block.hex())
        fd = parse_from_hex_blocks(blocks)
        assert fd.uid == bytes.fromhex("DEADBEEF")


class TestProxmark3Dump:
    def test_valid_dump(self):
        data = make_binary_dump()
        lines = []
        for i in range(TOTAL_BLOCKS):
            block = data[i * BYTES_PER_BLOCK:(i + 1) * BYTES_PER_BLOCK]
            hex_bytes = " ".join(f"{b:02X}" for b in block)
            lines.append(f"Block {i:02d}: {hex_bytes}")
        dump_text = "\n".join(lines)

        fd = parse_proxmark3_dump(dump_text)
        assert fd.uid == bytes.fromhex("DEADBEEF")

    def test_dump_with_comments(self):
        data = make_binary_dump()
        lines = ["# Proxmark3 dump", ""]
        for i in range(TOTAL_BLOCKS):
            block = data[i * BYTES_PER_BLOCK:(i + 1) * BYTES_PER_BLOCK]
            hex_bytes = " ".join(f"{b:02X}" for b in block)
            lines.append(f"Block {i:02d}: {hex_bytes}")
        dump_text = "\n".join(lines)

        fd = parse_proxmark3_dump(dump_text)
        assert fd.uid == bytes.fromhex("DEADBEEF")

    def test_incomplete_dump_raises(self):
        with pytest.raises(ValueError):
            parse_proxmark3_dump("Block 00: " + " ".join(["00"] * 16))
