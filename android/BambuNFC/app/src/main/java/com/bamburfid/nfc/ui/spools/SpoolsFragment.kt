package com.bamburfid.nfc.ui.spools

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import com.bamburfid.nfc.R

class SpoolsFragment : Fragment() {

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        val view = inflater.inflate(R.layout.fragment_stub, container, false)
        view.findViewById<TextView>(R.id.stubTitle).text = "Spool Inventory"
        view.findViewById<TextView>(R.id.stubDesc).text =
            "Manage your filament spool collection.\nConnect to server in Settings first."
        return view
    }
}
