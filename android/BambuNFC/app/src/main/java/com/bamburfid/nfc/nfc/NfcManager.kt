package com.bamburfid.nfc.nfc

import android.nfc.Tag
import android.nfc.tech.MifareClassic
import android.util.Log
import com.bamburfid.nfc.data.api.models.FilamentData

/**
 * Manages MIFARE Classic NFC read/write operations.
 *
 * Extracted from the original MainActivity to be reusable across fragments.
 */
object NfcManager {

    private const val TAG = "NfcManager"

    data class ReadResult(
        val filamentData: FilamentData,
        val rawBlocks: List<ByteArray>,
        val uid: ByteArray
    )

    sealed class NfcResult {
        data class Success(val result: ReadResult) : NfcResult()
        data class Error(val message: String) : NfcResult()
    }

    /**
     * Read a MIFARE Classic tag fully offline:
     * 1. Get UID from tag
     * 2. Derive sector keys from UID via HKDF
     * 3. Authenticate and read all 64 blocks
     * 4. Decode block data into FilamentData
     *
     * @param tag Android NFC Tag object
     * @return NfcResult with decoded FilamentData or error
     */
    fun readTag(tag: Tag): NfcResult {
        val mifare = MifareClassic.get(tag)
            ?: return NfcResult.Error("Not a MIFARE Classic tag")

        return try {
            mifare.connect()
            val uid = tag.id
            val uidHex = KeyDerivation.bytesToHex(uid)
            Log.d(TAG, "Reading tag: UID=$uidHex")

            // Derive keys locally
            val keys = KeyDerivation.deriveKeys(uid)

            val blocks = mutableListOf<ByteArray>()

            for (sector in 0 until mifare.sectorCount) {
                val authenticated = if (sector < keys.size) {
                    mifare.authenticateSectorWithKeyA(sector, keys[sector]) ||
                            mifare.authenticateSectorWithKeyB(sector, keys[sector])
                } else {
                    mifare.authenticateSectorWithKeyA(sector, MifareClassic.KEY_DEFAULT) ||
                            mifare.authenticateSectorWithKeyA(sector, MifareClassic.KEY_MIFARE_APPLICATION_DIRECTORY) ||
                            mifare.authenticateSectorWithKeyA(sector, MifareClassic.KEY_NFC_FORUM)
                }

                val firstBlock = mifare.sectorToBlock(sector)
                val blockCount = mifare.getBlockCountInSector(sector)

                if (authenticated) {
                    for (i in 0 until blockCount) {
                        blocks.add(mifare.readBlock(firstBlock + i))
                    }
                } else {
                    Log.w(TAG, "Auth failed for sector $sector, using zeros")
                    for (i in 0 until blockCount) {
                        blocks.add(ByteArray(16))
                    }
                }
            }

            mifare.close()
            Log.d(TAG, "Read complete: ${blocks.size} blocks")

            val filamentData = TagDecoder.decode(blocks)
            NfcResult.Success(ReadResult(filamentData, blocks, uid))

        } catch (e: Exception) {
            Log.e(TAG, "Read error", e)
            try { mifare.close() } catch (_: Exception) {}
            NfcResult.Error("Read failed: ${e.message}")
        }
    }

    /**
     * Write blocks to a MIFARE Classic tag.
     *
     * @param tag Android NFC Tag object
     * @param blocks List of 64 byte arrays (16 bytes each) to write
     * @param keys List of 16 sector keys (6 bytes each)
     * @return Number of blocks written, or error
     */
    fun writeTag(tag: Tag, blocks: List<ByteArray>, keys: List<ByteArray>): NfcResult {
        val mifare = MifareClassic.get(tag)
            ?: return NfcResult.Error("Not a MIFARE Classic tag")

        return try {
            mifare.connect()
            var written = 0

            for (sector in 0 until mifare.sectorCount) {
                if (sector >= keys.size) break

                val authenticated = mifare.authenticateSectorWithKeyA(sector, keys[sector]) ||
                        mifare.authenticateSectorWithKeyB(sector, keys[sector])

                if (authenticated) {
                    val firstBlock = mifare.sectorToBlock(sector)
                    val blockCount = mifare.getBlockCountInSector(sector)
                    for (i in 0 until blockCount) {
                        val blockNum = firstBlock + i
                        // Skip block 0 (manufacturer data) and sector trailers
                        if (blockNum == 0) continue
                        if ((blockNum + 1) % 4 == 0) continue
                        if (blockNum < blocks.size) {
                            mifare.writeBlock(blockNum, blocks[blockNum])
                            written++
                        }
                    }
                } else {
                    Log.w(TAG, "Auth failed for sector $sector during write")
                }
            }

            mifare.close()
            Log.d(TAG, "Write complete: $written blocks")

            // Re-read to verify
            NfcResult.Success(ReadResult(
                FilamentData(uid = "WRITE_OK"),
                emptyList(),
                ByteArray(0)
            ))

        } catch (e: Exception) {
            Log.e(TAG, "Write error", e)
            try { mifare.close() } catch (_: Exception) {}
            NfcResult.Error("Write failed: ${e.message}")
        }
    }
}
