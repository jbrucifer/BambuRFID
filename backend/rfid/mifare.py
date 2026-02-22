"""
MIFARE Classic 1K constants and structure definitions.

A MIFARE Classic 1K tag has:
- 16 sectors (0-15)
- 4 blocks per sector (64 blocks total, numbered 0-63)
- 16 bytes per block (1024 bytes total)
- Block 0: manufacturer data (read-only, contains UID)
- Every 4th block (3, 7, 11, ...): sector trailer (Key A + access bits + Key B)
"""

# Tag geometry
NUM_SECTORS = 16
BLOCKS_PER_SECTOR = 4
BYTES_PER_BLOCK = 16
TOTAL_BLOCKS = NUM_SECTORS * BLOCKS_PER_SECTOR  # 64
TOTAL_BYTES = TOTAL_BLOCKS * BYTES_PER_BLOCK  # 1024

# Sector trailer layout within a 16-byte block
KEY_A_OFFSET = 0
KEY_A_LENGTH = 6
ACCESS_BITS_OFFSET = 6
ACCESS_BITS_LENGTH = 4
KEY_B_OFFSET = 10
KEY_B_LENGTH = 6

# Default MIFARE keys
DEFAULT_KEY_A = bytes([0xFF] * 6)
DEFAULT_KEY_B = bytes([0xFF] * 6)


def sector_to_block(sector: int) -> int:
    """Return the first block number for a given sector."""
    return sector * BLOCKS_PER_SECTOR


def block_to_sector(block: int) -> int:
    """Return the sector number for a given block."""
    return block // BLOCKS_PER_SECTOR


def is_sector_trailer(block: int) -> bool:
    """Check if a block number is a sector trailer."""
    return (block + 1) % BLOCKS_PER_SECTOR == 0


def sector_trailer_block(sector: int) -> int:
    """Return the sector trailer block number for a given sector."""
    return sector_to_block(sector) + BLOCKS_PER_SECTOR - 1


def data_blocks_for_sector(sector: int) -> list[int]:
    """Return the data block numbers (non-trailer) for a given sector."""
    first = sector_to_block(sector)
    return [first + i for i in range(BLOCKS_PER_SECTOR - 1)]


def all_data_blocks() -> list[int]:
    """Return all data block numbers (excluding sector trailers)."""
    blocks = []
    for s in range(NUM_SECTORS):
        blocks.extend(data_blocks_for_sector(s))
    return blocks


def block_to_byte_offset(block: int) -> int:
    """Return the byte offset in a full 1K dump for a given block."""
    return block * BYTES_PER_BLOCK


def parse_sector_trailer(data: bytes) -> dict:
    """
    Parse a 16-byte sector trailer block.

    Returns dict with key_a, access_bits, and key_b as bytes.
    """
    if len(data) != BYTES_PER_BLOCK:
        raise ValueError(f"Sector trailer must be {BYTES_PER_BLOCK} bytes, got {len(data)}")
    return {
        "key_a": data[KEY_A_OFFSET:KEY_A_OFFSET + KEY_A_LENGTH],
        "access_bits": data[ACCESS_BITS_OFFSET:ACCESS_BITS_OFFSET + ACCESS_BITS_LENGTH],
        "key_b": data[KEY_B_OFFSET:KEY_B_OFFSET + KEY_B_LENGTH],
    }
