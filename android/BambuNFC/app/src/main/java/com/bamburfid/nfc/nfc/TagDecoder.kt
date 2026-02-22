package com.bamburfid.nfc.nfc

import com.bamburfid.nfc.data.api.models.FilamentData
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Decode raw MIFARE Classic 1K block data into FilamentData.
 *
 * Port of backend/rfid/bambu_format.py parse_tag_dump()
 *
 * All multi-byte numeric values are Little Endian.
 */
object TagDecoder {

    // RSA signature data blocks (sectors 10-15, excluding trailers)
    private val RSA_DATA_BLOCKS: List<Int> = buildList {
        for (sector in 10..15) {
            for (i in 0..2) {
                add(sector * 4 + i)
            }
        }
    }

    /**
     * Parse 64 blocks of 16 bytes each into FilamentData.
     *
     * @param blocks List of 64 byte arrays, each 16 bytes
     * @return Parsed FilamentData
     */
    fun decode(blocks: List<ByteArray>): FilamentData {
        require(blocks.size == 64) { "Expected 64 blocks, got ${blocks.size}" }

        // -- Sector 0 --
        // Block 0: UID (bytes 0-3) + manufacturer data
        val uid = blocks[0].copyOfRange(0, 4)
        val uidHex = KeyDerivation.bytesToHex(uid)

        // Block 1: Material variant ID (bytes 0-7) + Material ID (bytes 8-15)
        val materialVariantId = readString(blocks[1], 0, 8)
        val materialId = readString(blocks[1], 8, 8)

        // Block 2: Filament type (short)
        val filamentType = readString(blocks[2], 0, 16)

        // -- Sector 1 --
        // Block 4: Detailed filament type
        val detailedFilamentType = readString(blocks[4], 0, 16)

        // Block 5: Color RGBA (0-3) + spool weight uint16 LE (4-5) + diameter float LE (8-11)
        val colorR = blocks[5][0].toInt() and 0xFF
        val colorG = blocks[5][1].toInt() and 0xFF
        val colorB = blocks[5][2].toInt() and 0xFF
        val colorA = blocks[5][3].toInt() and 0xFF
        val colorHex = "#%02X%02X%02X".format(colorR, colorG, colorB)
        val spoolWeightG = readUint16LE(blocks[5], 4)
        val filamentDiameterMm = readFloatLE(blocks[5], 8)

        // Block 6: Temperatures
        val dryingTempC = readUint16LE(blocks[6], 0)
        val dryingTimeH = readUint16LE(blocks[6], 2)
        val bedTempType = readUint16LE(blocks[6], 4)
        val bedTempC = readUint16LE(blocks[6], 6)
        val maxHotendTempC = readUint16LE(blocks[6], 8)
        val minHotendTempC = readUint16LE(blocks[6], 10)

        // -- Sector 2 --
        // Block 8: X Cam info (0-11) + nozzle diameter float LE (12-15)
        val nozzleDiameter = readFloatLE(blocks[8], 12)

        // Block 9: Tray UID
        val trayUid = readString(blocks[9], 0, 16)

        // Block 10: Spool width (bytes 4-5, stored as mm*100)
        val rawWidth = readUint16LE(blocks[10], 4)
        val spoolWidthMm = rawWidth / 100f

        // -- Sector 3 --
        // Block 12: Production datetime
        val productionDatetime = readString(blocks[12], 0, 16)

        // Block 14: Filament length in meters (bytes 4-5)
        val filamentLengthM = readUint16LE(blocks[14], 4)

        // -- Sector 4 --
        // Block 16: Multi-color info
        val colorFormat = readUint16LE(blocks[16], 0)
        val colorCount = readUint16LE(blocks[16], 2)

        // -- Sectors 10-15: RSA Signature --
        val sigBytes = ByteArray(256)
        var sigOffset = 0
        for (blkNum in RSA_DATA_BLOCKS) {
            if (blkNum < blocks.size) {
                val chunk = blocks[blkNum]
                val copyLen = minOf(16, 256 - sigOffset)
                if (copyLen > 0) {
                    System.arraycopy(chunk, 0, sigBytes, sigOffset, copyLen)
                    sigOffset += copyLen
                }
            }
        }
        val hasRsaSignature = sigBytes.any { it.toInt() != 0 }

        return FilamentData(
            uid = uidHex,
            materialVariantId = materialVariantId,
            materialId = materialId,
            filamentType = filamentType,
            detailedFilamentType = detailedFilamentType,
            colorHex = colorHex,
            colorAlpha = colorA,
            spoolWeightG = spoolWeightG,
            filamentDiameterMm = filamentDiameterMm,
            dryingTempC = dryingTempC,
            dryingTimeH = dryingTimeH,
            bedTempType = bedTempType,
            bedTempC = bedTempC,
            maxHotendTempC = maxHotendTempC,
            minHotendTempC = minHotendTempC,
            nozzleDiameter = nozzleDiameter,
            trayUid = trayUid,
            spoolWidthMm = spoolWidthMm,
            productionDatetime = productionDatetime,
            filamentLengthM = filamentLengthM,
            colorFormat = colorFormat,
            colorCount = colorCount,
            hasRsaSignature = hasRsaSignature
        )
    }

    private fun readString(data: ByteArray, start: Int, length: Int): String {
        val end = minOf(start + length, data.size)
        val raw = data.copyOfRange(start, end)
        // Find null terminator
        val nullIdx = raw.indexOf(0)
        val trimmed = if (nullIdx >= 0) raw.copyOfRange(0, nullIdx) else raw
        return String(trimmed, Charsets.US_ASCII).trim()
    }

    private fun readUint16LE(data: ByteArray, offset: Int): Int {
        if (offset + 2 > data.size) return 0
        return (data[offset].toInt() and 0xFF) or
                ((data[offset + 1].toInt() and 0xFF) shl 8)
    }

    private fun readFloatLE(data: ByteArray, offset: Int): Float {
        if (offset + 4 > data.size) return 0f
        val buf = ByteBuffer.wrap(data, offset, 4).order(ByteOrder.LITTLE_ENDIAN)
        return buf.float
    }
}
