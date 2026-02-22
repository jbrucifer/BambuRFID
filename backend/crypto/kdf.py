"""
HKDF-SHA256 key derivation for Bambu Lab MIFARE Classic 1K RFID tags.

Each Bambu Lab filament spool uses a MIFARE Classic 1K tag with 16 sectors.
Every sector is encrypted with a unique 6-byte key derived from the tag's UID
using HKDF-SHA256 with a known master key and context string.

Reference: https://github.com/Bambu-Research-Group/RFID-Tag-Guide
"""

try:
    from Cryptodome.Protocol.KDF import HKDF
    from Cryptodome.Hash import SHA256
except ImportError:
    from Crypto.Protocol.KDF import HKDF
    from Crypto.Hash import SHA256

# Hardcoded master key discovered by the community
MASTER_KEY = bytes([
    0x9A, 0x75, 0x9C, 0xF2, 0xC4, 0xF7, 0xCA, 0xFF,
    0x22, 0x2C, 0xB9, 0x76, 0x9B, 0x41, 0xBC, 0x96,
])

# HKDF context string (null-terminated)
CONTEXT = b"RFID-A\x00"

# Number of sectors in MIFARE Classic 1K
NUM_SECTORS = 16

# Each MIFARE key is 6 bytes
KEY_LENGTH = 6


def derive_keys(uid: bytes) -> list[bytes]:
    """
    Derive 16 sector keys from a MIFARE Classic 1K tag UID.

    Args:
        uid: The tag UID as bytes (typically 4 bytes for MIFARE Classic).

    Returns:
        A list of 16 keys, each 6 bytes, one per sector.
    """
    raw = HKDF(
        master=uid,
        key_len=KEY_LENGTH,
        salt=MASTER_KEY,
        hashmod=SHA256,
        num_keys=NUM_SECTORS,
        context=CONTEXT,
    )
    # HKDF with num_keys > 1 returns a list of byte strings
    if isinstance(raw, list):
        return raw
    # Fallback: split a single bytes object into 16 chunks of 6
    return [raw[i * KEY_LENGTH:(i + 1) * KEY_LENGTH] for i in range(NUM_SECTORS)]


def derive_keys_from_hex(uid_hex: str) -> list[str]:
    """
    Convenience wrapper that accepts and returns hex strings.

    Args:
        uid_hex: The tag UID as a hex string (e.g. "7AD43F1C").

    Returns:
        A list of 16 hex-encoded keys (uppercase).
    """
    uid = bytes.fromhex(uid_hex)
    keys = derive_keys(uid)
    return [k.hex().upper() for k in keys]
