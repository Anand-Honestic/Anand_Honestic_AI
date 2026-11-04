package ai.honestic.athena.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import ai.honestic.athena.R
import ai.honestic.athena.service.AthenaForegroundService

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Ensure foreground service is running
        AthenaForegroundService.start(this)
    }

    fun openWhitelistSettings() {
        startActivity(Intent(this, WhitelistManagerActivity::class.java))
    }

    fun triggerLocalKillSwitch() {
        AthenaForegroundService.stop(this)
        Toast.makeText(this, "Emergency Kill Switch Activated: Sockets terminated.", Toast.LENGTH_LONG).show()
        finishAffinity()
    }
}

