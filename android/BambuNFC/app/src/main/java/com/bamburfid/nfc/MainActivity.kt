package com.bamburfid.nfc

import android.app.PendingIntent
import android.content.Intent
import android.content.IntentFilter
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.MifareClassic
import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.setupWithNavController
import com.bamburfid.nfc.databinding.ActivityMainBinding
import com.bamburfid.nfc.nfc.NfcManager
import com.bamburfid.nfc.ui.scan.ScanFragment
import com.bamburfid.nfc.ui.write.WriteFragment
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * BambuNFC — Enhanced companion app for BambuRFID.
 *
 * Single Activity with bottom navigation hosting 5 fragments.
 * NFC foreground dispatch is handled here and routed to the active fragment.
 */
class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "BambuNFC"
    }

    private lateinit var binding: ActivityMainBinding
    private var nfcAdapter: NfcAdapter? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Set up navigation
        val navHostFragment = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        val navController = navHostFragment.navController
        binding.bottomNav.setupWithNavController(navController)

        // Initialize NFC
        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
        if (nfcAdapter == null) {
            Snackbar.make(binding.root, R.string.nfc_not_available, Snackbar.LENGTH_LONG).show()
        } else if (!nfcAdapter!!.isEnabled) {
            Snackbar.make(binding.root, R.string.nfc_not_enabled, Snackbar.LENGTH_LONG).show()
        }
    }

    override fun onResume() {
        super.onResume()
        enableNfcForegroundDispatch()
    }

    override fun onPause() {
        super.onPause()
        nfcAdapter?.disableForegroundDispatch(this)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)

        if (NfcAdapter.ACTION_TECH_DISCOVERED == intent.action ||
            NfcAdapter.ACTION_TAG_DISCOVERED == intent.action) {

            @Suppress("DEPRECATION")
            val tag = intent.getParcelableExtra<Tag>(NfcAdapter.EXTRA_TAG)
            if (tag != null) {
                routeTagToFragment(tag)
            }
        }
    }

    private fun enableNfcForegroundDispatch() {
        val intent = Intent(this, javaClass).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent, PendingIntent.FLAG_MUTABLE
        )
        val filters = arrayOf(
            IntentFilter(NfcAdapter.ACTION_TAG_DISCOVERED),
            IntentFilter(NfcAdapter.ACTION_TECH_DISCOVERED)
        )
        val techList = arrayOf(
            arrayOf(MifareClassic::class.java.name)
        )
        nfcAdapter?.enableForegroundDispatch(this, pendingIntent, filters, techList)
    }

    /**
     * Route a discovered NFC tag to the currently visible fragment.
     * - ScanFragment: read and display the tag data
     * - WriteFragment: write pending data to the tag
     * - Any other screen: auto-read and show a snackbar summary
     */
    private fun routeTagToFragment(tag: Tag) {
        val navHostFragment = supportFragmentManager
            .findFragmentById(R.id.nav_host_fragment) as? NavHostFragment
        val currentFragment = navHostFragment?.childFragmentManager?.fragments?.firstOrNull()

        when (currentFragment) {
            is ScanFragment -> {
                Log.d(TAG, "Routing tag to ScanFragment")
                currentFragment.onTagDiscovered(tag)
            }
            is WriteFragment -> {
                Log.d(TAG, "Routing tag to WriteFragment")
                currentFragment.onTagDiscovered(tag)
            }
            else -> {
                // Auto-read from any screen and show snackbar
                Log.d(TAG, "Auto-reading tag from ${currentFragment?.javaClass?.simpleName}")
                autoReadTag(tag)
            }
        }
    }

    /**
     * Quick auto-read when tag is tapped from a non-Scan screen.
     * Shows a snackbar with the material name and navigates to Scan tab.
     */
    private fun autoReadTag(tag: Tag) {
        CoroutineScope(Dispatchers.IO).launch {
            val result = NfcManager.readTag(tag)
            when (result) {
                is NfcManager.NfcResult.Success -> {
                    val data = result.result.filamentData
                    runOnUiThread {
                        Snackbar.make(
                            binding.root,
                            "Tag: ${data.displayName} (${data.colorHex})",
                            Snackbar.LENGTH_LONG
                        ).setAction("View") {
                            binding.bottomNav.selectedItemId = R.id.scanFragment
                        }.show()
                    }
                }
                is NfcManager.NfcResult.Error -> {
                    runOnUiThread {
                        Snackbar.make(binding.root, result.message, Snackbar.LENGTH_SHORT).show()
                    }
                }
            }
        }
    }
}
