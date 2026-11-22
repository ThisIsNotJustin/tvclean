package dev.tvclean.home

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import dev.tvclean.home.core.LINK_POLL_MS

class RedirectService : AccessibilityService() {
    private val handler = Handler(Looper.getMainLooper())

    private val poll = object : Runnable {
        override fun run() {
            val policy = Redirect.policy
            if (!policy.pollActive()) return
            if (rootInActiveWindow?.packageName?.toString() == AMAZON_PKG) {
                val id = focusedViewId(rootInActiveWindow, 0)
                if (policy.onLauncherFocus(id)) {
                    redirect("home tab poll")
                    updateEventTypes()
                    return
                }
            }
            handler.postDelayed(this, LINK_POLL_MS)
        }
    }

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
        handler.removeCallbacks(poll)
        return super.onUnbind(intent)
    }

    override fun onDestroy() {
        Redirect.onSessionChange = null
        handler.removeCallbacks(poll)
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
        handler.removeCallbacks(poll)
        if (Redirect.policy.pollActive()) handler.postDelayed(poll, LINK_POLL_MS)
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
        const val AMAZON_PKG = "com.amazon.tv.launcher"
        const val MAX_DEPTH = 30
    }
}
