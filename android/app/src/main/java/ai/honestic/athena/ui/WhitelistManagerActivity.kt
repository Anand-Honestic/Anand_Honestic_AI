package ai.honestic.athena.ui

import android.content.Context
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import ai.honestic.athena.service.AthenaAccessibilityService

/**
 * WhitelistManagerActivity — User-Controlled App Authorization UI
 *
 * Enforces the non-negotiable rule:
 * User-approved app whitelist only — no blanket control.
 * No unsupervised autonomous actions outside whitelist.
 */
class WhitelistManagerActivity : AppCompatActivity() {

    private val PREFS_NAME = "athena_whitelist_prefs"
    private val KEY_WHITELIST = "approved_packages"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
    }

    fun getInstalledLaunchableApps(): List<AppItem> {
        val pm = packageManager
        val apps = pm.getInstalledApplications(PackageManager.GET_META_DATA)
        val result = mutableListOf<AppItem>()

        for (app in apps) {
            // Filter only non-system or launchable applications
            if (pm.getLaunchIntentForPackage(app.packageName) != null) {
                val name = pm.getApplicationLabel(app).toString()
                result.add(AppItem(name, app.packageName, isWhitelisted(app.packageName)))
            }
        }
        return result.sortedBy { it.appName }
    }

    fun isWhitelisted(packageName: String): Boolean {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val set = prefs.getStringSet(KEY_WHITELIST, AthenaAccessibilityService.defaultWhitelist) ?: emptySet()
        return set.contains(packageName)
    }

    fun toggleAppWhitelist(packageName: String, isAllowed: Boolean) {
        val prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val current = (prefs.getStringSet(KEY_WHITELIST, AthenaAccessibilityService.defaultWhitelist) ?: emptySet()).toMutableSet()
        if (isAllowed) {
            current.add(packageName)
        } else {
            current.remove(packageName)
        }
        prefs.edit().putStringSet(KEY_WHITELIST, current).apply()
        // Sync directly to active accessibility service instance
        AthenaAccessibilityService.instance?.updateWhitelist(current)
    }

    data class AppItem(val appName: String, val packageName: String, var isEnabled: Boolean)
}

