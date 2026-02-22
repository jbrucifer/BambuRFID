"""
Sector authentication helpers for MIFARE Classic tags.

Provides utilities for building authentication command payloads
that the Android NFC bridge app uses to authenticate with tag sectors.
"""

from dataclasses import dataclass

from .kdf import derive_keys


@dataclass
class SectorAuth:
    """Authentication data for a single MIFARE Classic sector."""
    sector: int
    key: bytes
    key_hex: str


def get_sector_auths(uid: bytes) -> list[SectorAuth]:
    """
    Get authentication data for all 16 sectors of a tag.

    Args:
        uid: The tag UID as bytes.

    Returns:
        List of SectorAuth objects with derived keys.
    """
    keys = derive_keys(uid)
    return [
        SectorAuth(sector=i, key=k, key_hex=k.hex().upper())
        for i, k in enumerate(keys)
    ]


def get_auth_payload(uid: bytes) -> dict:
    """
    Build a JSON-serializable auth payload for the NFC bridge.

    Args:
        uid: The tag UID as bytes.

    Returns:
        Dict with uid and keys list for the Android bridge app.
    """
    keys = derive_keys(uid)
    return {
        "uid": uid.hex().upper(),
        "keys": [k.hex().upper() for k in keys],
    }
