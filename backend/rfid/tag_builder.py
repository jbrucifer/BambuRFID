"""
High-level tag building — converts FilamentData to various output formats.

Supports multiple output formats:
- Raw binary (1024 bytes)
- Hex string
- Base64 string
- Block-by-block lists (for NFC bridge)
"""

import base64

from .mifare import BYTES_PER_BLOCK
from .bambu_format import FilamentData, build_tag_blocks


def build_blocks(fd: FilamentData) -> list[bytes]:
    """Build a list of 64 blocks (each 16 bytes) from FilamentData."""
    return build_tag_blocks(fd)


def build_binary(fd: FilamentData) -> bytes:
    """Build a raw 1024-byte binary dump."""
    blocks = build_tag_blocks(fd)
    return b"".join(blocks)


def build_hex(fd: FilamentData) -> str:
    """Build a hex-encoded string (2048 chars)."""
    return build_binary(fd).hex().upper()


def build_base64(fd: FilamentData) -> str:
    """Build a base64-encoded string."""
    return base64.b64encode(build_binary(fd)).decode("ascii")


def build_base64_blocks(fd: FilamentData) -> list[str]:
    """Build a list of 64 base64-encoded blocks (for NFC bridge transport)."""
    blocks = build_tag_blocks(fd)
    return [base64.b64encode(b).decode("ascii") for b in blocks]


def build_hex_blocks(fd: FilamentData) -> list[str]:
    """Build a list of 64 hex-encoded block strings."""
    blocks = build_tag_blocks(fd)
    return [b.hex().upper() for b in blocks]


def build_proxmark3_dump(fd: FilamentData) -> str:
    """
    Build a Proxmark3-compatible text dump.

    Output format:
    Block 00: AA BB CC DD EE FF 00 11 22 33 44 55 66 77 88 99
    """
    blocks = build_tag_blocks(fd)
    lines = []
    for i, block in enumerate(blocks):
        hex_bytes = " ".join(f"{b:02X}" for b in block)
        lines.append(f"Block {i:02d}: {hex_bytes}")
    return "\n".join(lines)
