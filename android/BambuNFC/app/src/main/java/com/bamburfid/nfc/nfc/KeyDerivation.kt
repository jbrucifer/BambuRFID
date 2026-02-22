package com.bamburfid.nfc.nfc

import org.bouncycastle.crypto.digests.SHA256Digest
import org.bouncycastle.crypto.generators.HKDFBytesGenerator
import org.bouncycastle.crypto.params.HKDFParameters

/**
 * HKDF-SHA256 key derivation for Bambu Lab MIFARE Classic 1K RFID tags.
 *
 * Each sector is encrypted with a unique 6-byte key derived from the tag's UID
 * using HKDF-SHA256 with a known master key and context string.
 *
 * Port of backend/crypto/kdf.py
 */
object KeyDerivation {

    private val MASTER_KEY = byteArrayOf(
        0x9A.toByte(), 0x75.toByte(), 0x9C.toByte(), 0xF2.toByte(),
        0xC4.toByte(), 0xF7.toByte(), 0xCA.toByte(), 0xFF.toByte(),
        0x22.toByte(), 0x2C.toByte(), 0xB9.toByte(), 0x76.toByte(),
        0x9B.toByte(), 0x41.toByte(), 0xBC.toByte(), 0x96.toByte(),
    )

    private val CONTEXT = byteArrayOf(
        'R'.code.toByte(), 'F'.code.toByte(), 'I'.code.toByte(), 'D'.code.toByte(),
        '-'.code.toByte(), 'A'.code.toByte(), 0x00
    )

    private const val KEY_LENGTH = 6
    private const val NUM_SECTORS = 16

    /**
     * Derive 16 sector keys from a MIFARE Classic 1K tag UID.
     *
     * @param uid The tag UID as bytes (typically 4 bytes for MIFARE Classic).
     * @return A list of 16 keys, each 6 bytes, one per sector.
     */
    fun deriveKeys(uid: ByteArray): List<ByteArray> {
        val hkdf = HKDFBytesGenerator(SHA256Digest())
        // HKDF parameters: IKM = uid, salt = MASTER_KEY, info = CONTEXT
        hkdf.init(HKDFParameters(uid, MASTER_KEY, CONTEXT))

        val allKeys = ByteArray(KEY_LENGTH * NUM_SECTORS)
        hkdf.generateBytes(allKeys, 0, allKeys.size)

        return (0 until NUM_SECTORS).map { i ->
            allKeys.copyOfRange(i * KEY_LENGTH, (i + 1) * KEY_LENGTH)
        }
    }

    /**
     * Convenience wrapper that accepts and returns hex strings.
     */
    fun deriveKeysFromHex(uidHex: String): List<String> {
        val uid = hexToBytes(uidHex)
        return deriveKeys(uid).map { bytesToHex(it) }
    }

    fun hexToBytes(hex: String): ByteArray {
        val clean = hex.replace(" ", "")
        return ByteArray(clean.length / 2) { i ->
            clean.substring(i * 2, i * 2 + 2).toInt(16).toByte()
        }
    }

    fun bytesToHex(bytes: ByteArray): String {
        return bytes.joinToString("") { "%02X".format(it) }
    }
}
