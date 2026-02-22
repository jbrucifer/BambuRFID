package com.bamburfid.nfc.ui.write

import android.nfc.Tag
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment
import com.bamburfid.nfc.R

class WriteFragment : Fragment() {

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        val view = inflater.inflate(R.layout.fragment_stub, container, false)
        view.findViewById<TextView>(R.id.stubTitle).text = "Write / Clone"
        view.findViewById<TextView>(R.id.stubDesc).text =
            "Write custom tags or clone existing ones.\nComing in the next update."
        return view
    }

    fun onTagDiscovered(tag: Tag) {
        // Will handle write operations in Phase 3
    }
}
