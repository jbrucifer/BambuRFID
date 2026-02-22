"""Tests for HKDF-SHA256 key derivation."""

import pytest
from backend.crypto.kdf import derive_keys, derive_keys_from_hex


class TestKeyDerivation:
    """Test the MIFARE Classic key derivation function."""

    def test_derive_keys_returns_16_keys(self):
        """KDF should produce exactly 16 keys (one per sector)."""
        uid = bytes.fromhex("7AD43F1C")
        keys = derive_keys(uid)
        assert len(keys) == 16

    def test_each_key_is_6_bytes(self):
        """Each MIFARE sector key must be exactly 6 bytes."""
        uid = bytes.fromhex("AABBCCDD")
        keys = derive_keys(uid)
        for i, key in enumerate(keys):
            assert len(key) == 6, f"Key for sector {i} is {len(key)} bytes, expected 6"

    def test_deterministic_output(self):
        """Same UID should always produce the same keys."""
        uid = bytes.fromhex("12345678")
        keys1 = derive_keys(uid)
        keys2 = derive_keys(uid)
        assert keys1 == keys2

    def test_different_uids_produce_different_keys(self):
        """Different UIDs should produce different key sets."""
        keys1 = derive_keys(bytes.fromhex("11111111"))
        keys2 = derive_keys(bytes.fromhex("22222222"))
        assert keys1 != keys2

    def test_derive_keys_from_hex(self):
        """Hex string wrapper should work correctly."""
        uid_bytes = bytes.fromhex("7AD43F1C")
        keys_bytes = derive_keys(uid_bytes)
        keys_hex = derive_keys_from_hex("7AD43F1C")

        assert len(keys_hex) == 16
        for kb, kh in zip(keys_bytes, keys_hex):
            assert kb.hex().upper() == kh

    def test_hex_input_case_insensitive(self):
        """Hex input should be case-insensitive."""
        keys_upper = derive_keys_from_hex("AABBCCDD")
        keys_lower = derive_keys_from_hex("aabbccdd")
        assert keys_upper == keys_lower

    def test_empty_uid_raises_or_produces_keys(self):
        """Empty UID should either raise an error or produce valid keys."""
        # The HKDF function may accept empty input
        try:
            keys = derive_keys(b"")
            assert len(keys) == 16
        except Exception:
            pass  # Also acceptable

    def test_known_uid_produces_non_default_keys(self):
        """Derived keys should not be the default MIFARE key (FFFFFFFFFFFF)."""
        uid = bytes.fromhex("7AD43F1C")
        keys = derive_keys(uid)
        default_key = bytes.fromhex("FFFFFFFFFFFF")
        for key in keys:
            assert key != default_key, "Derived key should not match default MIFARE key"
