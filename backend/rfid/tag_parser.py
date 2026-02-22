"""
High-level tag parsing — converts raw binary tag dumps to FilamentData.

Supports multiple input formats:
- Raw binary dump (1024 bytes)
- Hex string dump
- Block-by-block list (64 × 16 bytes)
- Proxmark3 dump format
"""

import base64

from .mifare import TOTAL_BLOCKS, BYTES_PER_BLOCK, TOTAL_BYTES
from .bambu_format import FilamentData, parse_tag_dump


def parse_from_blocks(blocks: list[bytes]) -> FilamentData:
    """Parse from a list of 64 blocks (each 16 bytes)."""
    return parse_tag_dump(blocks)


def parse_from_binary(data: bytes) -> FilamentData:
    """Parse from a raw 1024-byte binary dump."""
    if len(data) != TOTAL_BYTES:
        raise ValueError(f"Expected {TOTAL_BYTES} bytes, got {len(data)}")
    blocks = [data[i * BYTES_PER_BLOCK:(i + 1) * BYTES_PER_BLOCK]
              for i in range(TOTAL_BLOCKS)]
    return parse_tag_dump(blocks)


def parse_from_hex(hex_string: str) -> FilamentData:
    """Parse from a hex-encoded string (2048 hex chars = 1024 bytes)."""
    clean = hex_string.replace(" ", "").replace("\n", "").replace("\r", "")
    data = bytes.fromhex(clean)
    return parse_from_binary(data)


def parse_from_base64(b64_string: str) -> FilamentData:
    """Parse from a base64-encoded string."""
    data = base64.b64decode(b64_string)
    return parse_from_binary(data)


def parse_from_base64_blocks(b64_blocks: list[str]) -> FilamentData:
    """Parse from a list of 64 base64-encoded blocks."""
    blocks = [base64.b64decode(b) for b in b64_blocks]
    return parse_tag_dump(blocks)


def parse_from_hex_blocks(hex_blocks: list[str]) -> FilamentData:
    """Parse from a list of 64 hex-encoded block strings."""
    blocks = [bytes.fromhex(h) for h in hex_blocks]
    return parse_tag_dump(blocks)


def parse_proxmark3_dump(dump_text: str) -> FilamentData:
    """
    Parse a Proxmark3 text dump format.

    Expected format (one block per line):
    Block 00: AA BB CC DD EE FF 00 11 22 33 44 55 66 77 88 99
    Block 01: ...
    """
    blocks = []
    for line in dump_text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Extract hex data after the colon
        if ":" in line:
            hex_part = line.split(":", 1)[1].strip()
        else:
            hex_part = line
        # Remove spaces and parse
        hex_clean = hex_part.replace(" ", "")
        if len(hex_clean) == 32:  # 16 bytes = 32 hex chars
            blocks.append(bytes.fromhex(hex_clean))

    if len(blocks) != TOTAL_BLOCKS:
        raise ValueError(
            f"Proxmark3 dump should have {TOTAL_BLOCKS} blocks, found {len(blocks)}"
        )
    return parse_tag_dump(blocks)
