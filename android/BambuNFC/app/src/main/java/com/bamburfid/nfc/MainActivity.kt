package com.bamburfid.nfc

import android.app.PendingIntent
import android.content.Intent
import android.content.IntentFilter
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.MifareClassic
import android.os.Bundle
import android.util.Base64
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONArray
import org.json.JSONObject
import java.net.URI
import okhttp3.*

/**
 * BambuNFC — Android companion app for BambuRFID.
 *
 * Acts as a MIFARE Classic NFC bridge between the phone's NFC hardware
 * and the BambuRFID web backend via WebSocket.
 */
class MainActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "BambuNFC"
    }

    private var nfcAdapter: NfcAdapter? = null
    private var wsClient: OkHttpClient? = null
    private var webSocket: WebSocket? = null
    private var connected = false

    // Current operation mode
    private var pendingAction: String? = null  // "READ_TAG" or "WRITE_TAG"
    private var pendingRequestId: String? = null
    private var pendingKeys: List<ByteArray>? = null
    private var pendingBlocks: List<ByteArray>? = null
    private var pendingTargetUid: ByteArray? = null

    // UI elements
    private lateinit var statusText: TextView
    private lateinit var logText: TextView
    private lateinit var serverInput: EditText
    private lateinit var connectButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        statusText = findViewById(R.id.statusText)
        logText = findViewById(R.id.logText)
        serverInput = findViewById(R.id.serverInput)
        connectButton = findViewById(R.id.connectButton)

        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
        if (nfcAdapter == null) {
            statusText.text = "NFC not available on this device"
            return
        }

        connectButton.setOnClickListener {
            val url = serverInput.text.toString().trim()
            if (url.isNotEmpty()) {
                connectWebSocket(url)
            }
        }

        log("BambuNFC ready. Enter server URL and tap Connect.")
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
            val tag = intent.getParcelableExtra<Tag>(NfcAdapter.EXTRA_TAG)
            if (tag != null) {
                handleTag(tag)
            }
        }
    }

    private fun enableNfcForegroundDispatch() {
        val intent = Intent(this, javaClass).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent, PendingIntent.FLAG_MUTABLE
        )
        val techFilter = IntentFilter(NfcAdapter.ACTION_TECH_DISCOVERED)
        val techList = arrayOf(arrayOf(MifareClassic::class.java.name))
        nfcAdapter?.enableForegroundDispatch(this, pendingIntent, arrayOf(techFilter), techList)
    }

    // ──────────────────────────────────────────
    // NFC Tag Handling
    // ──────────────────────────────────────────

    private fun handleTag(tag: Tag) {
        val mifare = MifareClassic.get(tag)
        if (mifare == null) {
            log("Not a MIFARE Classic tag")
            return
        }

        val uid = tag.id
        val uidHex = uid.joinToString("") { "%02X".format(it) }
        log("Tag detected: UID=$uidHex")

        // Notify backend of tag detection
        sendMessage(JSONObject().apply {
            put("action", "TAG_DETECTED")
            put("uid", uidHex)
        })

        when (pendingAction) {
            "READ_TAG" -> readTag(mifare, uid, uidHex)
            "WRITE_TAG" -> writeTag(mifare, uid, uidHex)
            else -> {
                // Auto-read if no specific action is pending
                log("No pending action. Auto-reading tag...")
                readTag(mifare, uid, uidHex)
            }
        }
    }

    private fun readTag(mifare: MifareClassic, uid: ByteArray, uidHex: String) {
        Thread {
            try {
                mifare.connect()
                log("Reading ${mifare.blockCount} blocks...")

                val blocks = JSONArray()
                val keys = pendingKeys

                for (sector in 0 until mifare.sectorCount) {
                    // Try to authenticate with derived key, then default keys
                    val authenticated = if (keys != null && sector < keys.size) {
                        mifare.authenticateSectorWithKeyA(sector, keys[sector]) ||
                        mifare.authenticateSectorWithKeyB(sector, keys[sector])
                    } else {
                        mifare.authenticateSectorWithKeyA(sector, MifareClassic.KEY_DEFAULT) ||
                        mifare.authenticateSectorWithKeyA(sector, MifareClassic.KEY_MIFARE_APPLICATION_DIRECTORY) ||
                        mifare.authenticateSectorWithKeyA(sector, MifareClassic.KEY_NFC_FORUM)
                    }

                    if (authenticated) {
                        val firstBlock = mifare.sectorToBlock(sector)
                        val blockCount = mifare.getBlockCountInSector(sector)
                        for (i in 0 until blockCount) {
                            val blockData = mifare.readBlock(firstBlock + i)
                            blocks.put(Base64.encodeToString(blockData, Base64.NO_WRAP))
                        }
                    } else {
                        log("Auth failed for sector $sector, using zeros")
                        val blockCount = mifare.getBlockCountInSector(sector)
                        for (i in 0 until blockCount) {
                            blocks.put(Base64.encodeToString(ByteArray(16), Base64.NO_WRAP))
                        }
                    }
                }

                mifare.close()
                log("Read complete: ${blocks.length()} blocks")

                // Send data to backend
                sendMessage(JSONObject().apply {
                    put("action", "TAG_DATA")
                    put("uid", uidHex)
                    put("blocks", blocks)
                    put("request_id", pendingRequestId ?: "")
                })

                pendingAction = null
                pendingRequestId = null
                runOnUiThread { statusText.text = "Tag read complete" }

            } catch (e: Exception) {
                log("Read error: ${e.message}")
                sendMessage(JSONObject().apply {
                    put("action", "ERROR")
                    put("message", "Read failed: ${e.message}")
                })
                try { mifare.close() } catch (_: Exception) {}
            }
        }.start()
    }

    private fun writeTag(mifare: MifareClassic, uid: ByteArray, uidHex: String) {
        val keys = pendingKeys
        val blocks = pendingBlocks

        if (keys == null || blocks == null) {
            log("No write data available")
            return
        }

        Thread {
            try {
                mifare.connect()
                log("Writing ${blocks.size} blocks...")

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
                            if ((blockNum + 1) % 4 == 0) continue  // Sector trailer
                            if (blockNum < blocks.size) {
                                mifare.writeBlock(blockNum, blocks[blockNum])
                                written++
                            }
                        }
                    } else {
                        log("Auth failed for sector $sector during write")
                    }
                }

                mifare.close()
                log("Write complete: $written blocks written")

                sendMessage(JSONObject().apply {
                    put("action", "WRITE_RESULT")
                    put("success", true)
                    put("blocks_written", written)
                    put("request_id", pendingRequestId ?: "")
                })

                pendingAction = null
                pendingRequestId = null
                pendingKeys = null
                pendingBlocks = null
                runOnUiThread { statusText.text = "Tag write complete" }

            } catch (e: Exception) {
                log("Write error: ${e.message}")
                sendMessage(JSONObject().apply {
                    put("action", "WRITE_RESULT")
                    put("success", false)
                    put("error", e.message)
                    put("request_id", pendingRequestId ?: "")
                })
                try { mifare.close() } catch (_: Exception) {}
            }
        }.start()
    }

    // ──────────────────────────────────────────
    // WebSocket Communication
    // ──────────────────────────────────────────

    private fun connectWebSocket(serverUrl: String) {
        val wsUrl = if (serverUrl.startsWith("ws://") || serverUrl.startsWith("wss://")) {
            serverUrl
        } else {
            "ws://$serverUrl/ws/nfc"
        }

        log("Connecting to $wsUrl...")
        wsClient = OkHttpClient()
        val request = Request.Builder().url(wsUrl).build()

        webSocket = wsClient?.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                connected = true
                log("Connected to server")
                runOnUiThread { statusText.text = "Connected to BambuRFID server" }

                // Send status
                sendMessage(JSONObject().apply {
                    put("action", "STATUS")
                    put("connected", true)
                    put("device", android.os.Build.MODEL)
                })
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleServerMessage(text)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                connected = false
                log("Disconnected: $reason")
                runOnUiThread { statusText.text = "Disconnected" }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                connected = false
                log("Connection error: ${t.message}")
                runOnUiThread { statusText.text = "Connection failed" }
            }
        })
    }

    private fun handleServerMessage(text: String) {
        try {
            val msg = JSONObject(text)
            val action = msg.optString("action", "")

            when (action) {
                "READ_TAG" -> {
                    pendingAction = "READ_TAG"
                    pendingRequestId = msg.optString("request_id", "")

                    // If keys are provided, parse them
                    if (msg.has("keys")) {
                        val keysArray = msg.getJSONArray("keys")
                        val keyList = mutableListOf<ByteArray>()
                        for (i in 0 until keysArray.length()) {
                            keyList.add(hexToBytes(keysArray.getString(i)))
                        }
                        pendingKeys = keyList
                    }

                    log("Server requested tag read. Tap a tag...")
                    runOnUiThread { statusText.text = "Tap a tag to read" }
                }

                "WRITE_TAG" -> {
                    pendingAction = "WRITE_TAG"
                    pendingRequestId = msg.optString("request_id", "")

                    // Parse keys
                    val keysArray = msg.getJSONArray("keys")
                    val keyList = mutableListOf<ByteArray>()
                    for (i in 0 until keysArray.length()) {
                        keyList.add(hexToBytes(keysArray.getString(i)))
                    }
                    pendingKeys = keyList

                    // Parse blocks
                    val blocksArray = msg.getJSONArray("blocks")
                    val blockList = mutableListOf<ByteArray>()
                    for (i in 0 until blocksArray.length()) {
                        blockList.add(Base64.decode(blocksArray.getString(i), Base64.NO_WRAP))
                    }
                    pendingBlocks = blockList

                    // Parse target UID for magic tags
                    if (msg.has("uid")) {
                        pendingTargetUid = hexToBytes(msg.getString("uid"))
                    }

                    log("Server requested tag write. Tap a blank tag...")
                    runOnUiThread { statusText.text = "Tap a tag to write" }
                }

                "DERIVE_KEYS" -> {
                    val uid = msg.getString("uid")
                    log("Received keys for UID: $uid")
                    // Keys will be used for next read/write operation
                }

                else -> log("Unknown action: $action")
            }
        } catch (e: Exception) {
            log("Message parse error: ${e.message}")
        }
    }

    private fun sendMessage(json: JSONObject) {
        webSocket?.send(json.toString())
    }

    // ──────────────────────────────────────────
    // Utility
    // ──────────────────────────────────────────

    private fun hexToBytes(hex: String): ByteArray {
        val clean = hex.replace(" ", "")
        return ByteArray(clean.length / 2) { i ->
            clean.substring(i * 2, i * 2 + 2).toInt(16).toByte()
        }
    }

    private fun log(message: String) {
        Log.d(TAG, message)
        runOnUiThread {
            logText.append("$message\n")
            // Auto-scroll to bottom
            val scrollAmount = logText.layout?.let {
                it.getLineTop(logText.lineCount) - logText.height
            } ?: 0
            if (scrollAmount > 0) {
                logText.scrollTo(0, scrollAmount)
            }
        }
    }
}
