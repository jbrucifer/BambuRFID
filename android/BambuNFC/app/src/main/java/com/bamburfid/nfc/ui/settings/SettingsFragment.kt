package com.bamburfid.nfc.ui.settings

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import com.bamburfid.nfc.R

class SettingsFragment : Fragment() {

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        val view = inflater.inflate(R.layout.fragment_stub, container, false)
        view.findViewById<TextView>(R.id.stubTitle).text = "Settings"
        view.findViewById<TextView>(R.id.stubDesc).text =
            "Server connection, printer config,\nbridge mode, and tools.\nComing in the next update."
        return view
    }
}
