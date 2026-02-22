package com.bamburfid.nfc.ui.scan

import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.nfc.Tag
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import com.bamburfid.nfc.data.api.models.FilamentData
import com.bamburfid.nfc.databinding.FragmentScanBinding

class ScanFragment : Fragment() {

    private var _binding: FragmentScanBinding? = null
    private val binding get() = _binding!!
    private val viewModel: ScanViewModel by viewModels()
    private var detailsExpanded = false

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentScanBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        binding.toggleDetails.setOnClickListener {
            detailsExpanded = !detailsExpanded
            binding.moreDetails.visibility = if (detailsExpanded) View.VISIBLE else View.GONE
            binding.toggleDetails.text = if (detailsExpanded) "Show less" else "Show more"
        }

        binding.btnSaveToInventory.setOnClickListener {
            // Will be implemented in Phase 2 (server connection)
            com.google.android.material.snackbar.Snackbar.make(
                binding.root, "Connect to server first (Settings tab)", com.google.android.material.snackbar.Snackbar.LENGTH_SHORT
            ).show()
        }

        binding.btnCloneTag.setOnClickListener {
            // Will be implemented in Phase 3 (write/clone)
            com.google.android.material.snackbar.Snackbar.make(
                binding.root, "Clone feature coming soon", com.google.android.material.snackbar.Snackbar.LENGTH_SHORT
            ).show()
        }

        viewModel.scanState.observe(viewLifecycleOwner) { state ->
            when (state) {
                is ScanViewModel.ScanState.Idle -> showIdle()
                is ScanViewModel.ScanState.Reading -> showReading()
                is ScanViewModel.ScanState.Success -> showSuccess()
                is ScanViewModel.ScanState.Error -> showError(state.message)
            }
        }

        viewModel.lastReadData.observe(viewLifecycleOwner) { data ->
            if (data != null) {
                displayFilamentData(data)
            }
        }
    }

    fun onTagDiscovered(tag: Tag) {
        viewModel.onTagDiscovered(tag)
    }

    private fun showIdle() {
        binding.scanPromptArea.visibility = View.VISIBLE
        binding.statusMessage.visibility = View.GONE
        binding.errorMessage.visibility = View.GONE
    }

    private fun showReading() {
        binding.scanPromptText.text = getString(com.bamburfid.nfc.R.string.scan_reading)
        binding.statusMessage.visibility = View.GONE
        binding.errorMessage.visibility = View.GONE
    }

    private fun showSuccess() {
        binding.scanPromptArea.visibility = View.GONE
        binding.statusMessage.text = getString(com.bamburfid.nfc.R.string.scan_success)
        binding.statusMessage.visibility = View.VISIBLE
        binding.errorMessage.visibility = View.GONE
        binding.filamentCard.visibility = View.VISIBLE
        binding.actionButtons.visibility = View.VISIBLE
    }

    private fun showError(message: String) {
        binding.scanPromptArea.visibility = View.VISIBLE
        binding.scanPromptText.text = getString(com.bamburfid.nfc.R.string.scan_prompt)
        binding.errorMessage.text = message
        binding.errorMessage.visibility = View.VISIBLE
        binding.statusMessage.visibility = View.GONE
    }

    private fun displayFilamentData(data: FilamentData) {
        // Header
        binding.materialName.text = data.displayName
        binding.materialId.text = buildString {
            if (data.materialId.isNotBlank()) append(data.materialId)
            if (data.materialVariantId.isNotBlank()) append(" / ${data.materialVariantId}")
        }

        // Color swatch
        try {
            val color = Color.parseColor(data.colorHex)
            val drawable = binding.colorSwatch.background as? GradientDrawable
            drawable?.setColor(color)
        } catch (_: Exception) {}

        // RSA badge
        binding.rsaBadge.visibility = if (data.hasRsaSignature) View.VISIBLE else View.GONE

        // Data grid
        binding.valueUid.text = data.uid
        binding.valueColor.text = data.colorHex
        binding.valueNozzleTemp.text = data.nozzleTempRange
        binding.valueBedTemp.text = if (data.bedTempC > 0) "${data.bedTempC}\u00B0C" else "N/A"
        binding.valueSpoolWeight.text = if (data.spoolWeightG > 0) "${data.spoolWeightG}g" else "N/A"
        binding.valueDiameter.text = "${data.filamentDiameterMm}mm"
        binding.valueLength.text = if (data.filamentLengthM > 0) "${data.filamentLengthM}m" else "N/A"

        // More details
        binding.valueDrying.text = if (data.dryingTempC > 0)
            "${data.dryingTempC}\u00B0C / ${data.dryingTimeH}h" else "N/A"
        binding.valueProductionDate.text = data.productionDatetime.ifBlank { "N/A" }
        binding.valueTrayUid.text = data.trayUid.ifBlank { "N/A" }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
