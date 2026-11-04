package ai.honestic.athena.ui

import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import ai.honestic.athena.R
import ai.honestic.athena.service.AthenaForegroundService

/**
 * OnboardingActivity — 5-Step Xiaomi HyperOS / Redmi 14C 5G Provisioning Wizard
 *
 * Steps:
 * 1. Battery Saver Exemption (Bypasses HyperOS process kill).
 * 2. Accessibility Permission with Google Play compliant Prominent Disclosure.
 * 3. Whitelisted Apps Selection.
 * 4. QR Code Pairing Scanner.
 * 5. Biometric Fingerprint/FaceID enrollment.
 */
class OnboardingActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Setup initial onboarding step
        checkBatteryOptimization()
    }

    /**
     * Step 1: Request exemption from Xiaomi HyperOS aggressive background killer.
     */
    private fun checkBatteryOptimization() {
        val powerManager = getSystemService(Context.POWER_SERVICE) as PowerManager
        if (!powerManager.isIgnoringBatteryOptimizations(packageName)) {
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                data = Uri.parse("package:$packageName")
            }
            try {
                startActivity(intent)
            } catch (e: Exception) {
                // HyperOS specific intent fallback
                val miuiIntent = Intent("miui.intent.action.POWER_HIDE_MODE_APP_LIST")
                try { startActivity(miuiIntent) } catch (_: Exception) {}
            }
        }
    }

    /**
     * Step 2: Display Prominent Disclosure before navigating to Accessibility settings.
     */
    fun promptAccessibilityDisclosure(onAccepted: () -> Unit) {
        AlertDialog.Builder(this)
            .setTitle(R.string.accessibility_disclosure_title)
            .setMessage(R.string.accessibility_disclosure_body)
            .setPositiveButton("Accept & Open Settings") { _, _ ->
                onAccepted()
                val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
                startActivity(intent)
                Toast.makeText(
                    this,
                    "HyperOS Tip: If grayed out, tap App Info -> 3 dots -> 'Allow restricted settings'",
                    Toast.LENGTH_LONG
                ).show()
            }
            .setNegativeButton("Decline", null)
            .setCancelable(false)
            .show()
    }

    /**
     * Step 4: Finish Pairing & Start Companion Service
     */
    fun completeOnboardingAndStartService() {
        AthenaForegroundService.start(this)
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
}

