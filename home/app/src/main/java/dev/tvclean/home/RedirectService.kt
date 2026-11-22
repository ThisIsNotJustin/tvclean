package dev.tvclean.home

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class RedirectService : AccessibilityService() {

    override fun onServiceConnected() {
        super.onServiceConnected()
        Redirect.onSessionChange = ::updateEventTypes
        updateEventTypes()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        val policy = Redirect.policy
        when (event.eventType) {
            AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> {
                val cls = event.className?.toString() ?: return
                if (cls.endsWith("HomeActivity_vNext") && policy.onAmazonHomeWindow()) {
                    redirect("window")
                    updateEventTypes()
                }
            }
            AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED -> {
                if (!policy.inLinkSession()) return
                val id = focusedViewId(rootInActiveWindow, 0)
                if (policy.onLauncherFocus(id)) {
                    redirect("home tab")
                    updateEventTypes()
                }
            }
        }
    }

    override fun onInterrupt() {}

    override fun onUnbind(intent: Intent?): Boolean {
        Redirect.onSessionChange = null
        return super.onUnbind(intent)
    }

    override fun onDestroy() {
        Redirect.onSessionChange = null
        super.onDestroy()
    }

    private fun redirect(reason: String) {
        Log.i(TAG, "redirect to Home ($reason)")
        startActivity(
            Intent(this, HomeActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
                .putExtra("from_redirect", true),
        )
    }

    /** First focused node with a view id. findFocus only returns the host view, not the Compose nodes. */
    private fun focusedViewId(node: AccessibilityNodeInfo?, depth: Int): String? {
        if (node == null || depth > MAX_DEPTH) return null
        if (node.isFocused) node.viewIdResourceName?.let { return it }
        for (i in 0 until node.childCount) {
            focusedViewId(node.getChild(i), depth + 1)?.let { return it }
        }
        return null
    }

    private fun updateEventTypes() {
        val info = serviceInfo ?: return
        var types = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
        if (Redirect.policy.inLinkSession()) types = types or AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED
        if (info.eventTypes != types) {
            info.eventTypes = types
            serviceInfo = info
        }
    }

    private companion object {
        const val TAG = "TVHOME"
        const val MAX_DEPTH = 30
    }
}
