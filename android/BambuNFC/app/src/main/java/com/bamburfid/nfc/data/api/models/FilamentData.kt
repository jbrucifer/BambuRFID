package com.bamburfid.nfc.data.api.models

import com.google.gson.annotations.SerializedName

/**
 * Decoded filament data from a Bambu Lab RFID tag.
 * Mirrors the backend's FilamentData.to_dict() output.
 */
data class FilamentData(
    val uid: String = "",

    @SerializedName("material_variant_id")
    val materialVariantId: String = "",

    @SerializedName("material_id")
    val materialId: String = "",

    @SerializedName("filament_type")
    val filamentType: String = "",

    @SerializedName("detailed_filament_type")
    val detailedFilamentType: String = "",

    @SerializedName("color_hex")
    val colorHex: String = "#000000",

    @SerializedName("color_alpha")
    val colorAlpha: Int = 255,

    @SerializedName("spool_weight_g")
    val spoolWeightG: Int = 0,

    @SerializedName("filament_diameter_mm")
    val filamentDiameterMm: Float = 1.75f,

    @SerializedName("drying_temp_c")
    val dryingTempC: Int = 0,

    @SerializedName("drying_time_h")
    val dryingTimeH: Int = 0,

    @SerializedName("bed_temp_type")
    val bedTempType: Int = 0,

    @SerializedName("bed_temp_c")
    val bedTempC: Int = 0,

    @SerializedName("max_hotend_temp_c")
    val maxHotendTempC: Int = 0,

    @SerializedName("min_hotend_temp_c")
    val minHotendTempC: Int = 0,

    @SerializedName("nozzle_diameter")
    val nozzleDiameter: Float = 0f,

    @SerializedName("tray_uid")
    val trayUid: String = "",

    @SerializedName("spool_width_mm")
    val spoolWidthMm: Float = 0f,

    @SerializedName("production_datetime")
    val productionDatetime: String = "",

    @SerializedName("filament_length_m")
    val filamentLengthM: Int = 0,

    @SerializedName("color_format")
    val colorFormat: Int = 0,

    @SerializedName("color_count")
    val colorCount: Int = 0,

    @SerializedName("has_rsa_signature")
    val hasRsaSignature: Boolean = false
) {
    /** Display name — prefer detailed type, fall back to short type */
    val displayName: String
        get() = detailedFilamentType.ifBlank { filamentType.ifBlank { "Unknown" } }

    /** Temperature range string */
    val nozzleTempRange: String
        get() = if (minHotendTempC > 0 && maxHotendTempC > 0)
            "${minHotendTempC}-${maxHotendTempC}\u00B0C" else "N/A"
}
