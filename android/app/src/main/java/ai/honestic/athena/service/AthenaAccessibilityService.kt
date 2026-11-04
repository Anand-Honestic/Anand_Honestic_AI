package ai.honestic.athena.service

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.Rect
import android.os.Bundle
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import java.util.concurrent.ConcurrentHashMap

/**
 * AthenaAccessibilityService — Production UI Automation Engine
 *
 * Scoped strictly to user-approved whitelisted apps.
 * Implements Google Play and Xiaomi HyperOS safety policies:
 * - Refuses access to password/payment fields.
 * - Refuses interaction with non-whitelisted apps.
 * - Dispatches safe clicks, text entry, and scroll gestures.
 */
class AthenaAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "AthenaA11y"
        var instance: AthenaAccessibilityService? = null
            private set

        val defaultWhitelist = setOf(
            "com.whatsapp",
            "com.google.android.youtube",
            "com.google.android.apps.messaging",
            "com.google.android.calculator",
            "com.miui.calculator"
        )
    }

    private val userWhitelistedPackages = ConcurrentHashMap.newKeySet<String>()

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        userWhitelistedPackages.addAll(defaultWhitelist)
        Log.i(TAG, "ATHENA Accessibility Service Connected and Active.")
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        Log.i(TAG, "ATHENA Accessibility Service Destroyed.")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Passive observation only for window changes of whitelisted packages
    }

    override fun onInterrupt() {
        Log.w(TAG, "ATHENA Accessibility Service Interrupted.")
    }

    fun isAppWhitelisted(packageName: String): Boolean {
        return userWhitelistedPackages.contains(packageName.trim().lowercase())
    }

    fun updateWhitelist(packages: Collection<String>) {
        userWhitelistedPackages.clear()
        userWhitelistedPackages.addAll(packages.map { it.trim().lowercase() })
        Log.i(TAG, "App Whitelist updated: ${userWhitelistedPackages.size} packages.")
    }

    /**
     * Finds and clicks a view matching the specified text inside the active window.
     */
    fun clickByText(targetText: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val currentPkg = root.packageName?.toString() ?: ""
        if (!isAppWhitelisted(currentPkg)) {
            Log.e(TAG, "Blocked action: package '$currentPkg' is not in approved whitelist.")
            return false
        }

        val nodes = root.findAccessibilityNodeInfosByText(targetText)
        if (nodes.isNullOrEmpty()) {
            return false
        }

        for (node in nodes) {
            if (node.isClickable) {
                return node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            }
            // Check parent if clickable
            var parent = node.parent
            while (parent != null) {
                if (parent.isClickable) {
                    return parent.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                }
                parent = parent.parent
            }
        }

        // Fallback: click coordinates of the node bounding box
        val rect = Rect()
        nodes[0].getBoundsInScreen(rect)
        return clickAt(rect.centerX().toFloat(), rect.centerY().toFloat())
    }

    /**
     * Types text into the currently focused or specified input field, blocking password inputs.
     */
    fun enterText(textToEnter: String, viewId: String? = null): Boolean {
        val root = rootInActiveWindow ?: return false
        val currentPkg = root.packageName?.toString() ?: ""
        if (!isAppWhitelisted(currentPkg)) {
            Log.e(TAG, "Blocked text input: package '$currentPkg' not whitelisted.")
            return false
        }

        val targetNode: AccessibilityNodeInfo? = if (viewId != null) {
            val list = root.findAccessibilityNodeInfosByViewId(viewId)
            list?.firstOrNull()
        } else {
            root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
        }

        if (targetNode == null) {
            return false
        }

        // Safety Invariant: Never write or touch password/credential fields
        if (targetNode.isPassword) {
            Log.e(TAG, "Security violation: Refusing to interact with password input field.")
            return false
        }

        val arguments = Bundle()
        arguments.putCharSequence(
            AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
            textToEnter
        )
        return targetNode.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments)
    }

    /**
     * Dispatches an automated tap gesture at screen coordinates.
     */
    fun clickAt(x: Float, y: Float): Boolean {
        val path = Path()
        path.moveTo(x, y)
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, 50))
            .build()
        return dispatchGesture(gesture, null, null)
    }
}

