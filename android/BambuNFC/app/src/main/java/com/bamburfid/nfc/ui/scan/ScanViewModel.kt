package com.bamburfid.nfc.ui.scan

import android.nfc.Tag
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bamburfid.nfc.data.api.models.FilamentData
import com.bamburfid.nfc.nfc.NfcManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class ScanViewModel : ViewModel() {

    private val _scanState = MutableLiveData<ScanState>(ScanState.Idle)
    val scanState: LiveData<ScanState> = _scanState

    private val _lastReadData = MutableLiveData<FilamentData?>()
    val lastReadData: LiveData<FilamentData?> = _lastReadData

    private var _lastRawBlocks: List<ByteArray>? = null
    val lastRawBlocks: List<ByteArray>? get() = _lastRawBlocks

    private var _lastUid: ByteArray? = null
    val lastUid: ByteArray? get() = _lastUid

    fun onTagDiscovered(tag: Tag) {
        _scanState.value = ScanState.Reading

        viewModelScope.launch(Dispatchers.IO) {
            val result = NfcManager.readTag(tag)

            when (result) {
                is NfcManager.NfcResult.Success -> {
                    _lastRawBlocks = result.result.rawBlocks
                    _lastUid = result.result.uid
                    _lastReadData.postValue(result.result.filamentData)
                    _scanState.postValue(ScanState.Success)
                }
                is NfcManager.NfcResult.Error -> {
                    _scanState.postValue(ScanState.Error(result.message))
                }
            }
        }
    }

    sealed class ScanState {
        object Idle : ScanState()
        object Reading : ScanState()
        object Success : ScanState()
        data class Error(val message: String) : ScanState()
    }
}
