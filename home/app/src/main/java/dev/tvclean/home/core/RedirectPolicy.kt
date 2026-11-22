package dev.tvclean.home.core

/** Decides when Amazon Home appearing should send the owner back to our Home. True = redirect now. */
class RedirectPolicy(private val now: () -> Long) {
    private var pausedUntil = 0L
    private var inSession = false
    private var sessionStart = 0L

    fun pauseFor(ms: Long) {
        pausedUntil = now() + ms
        inSession = false
    }

    fun isPaused(): Boolean = now() < pausedUntil

    fun startLinkSession() {
        inSession = true
        sessionStart = now()
    }

    /** The delayed tab link was actually sent: restart the grace window. */
    fun renewGrace() {
        if (inSession) sessionStart = now()
    }

    /** True while a link session should be polled: active and within the cap since it started or was renewed. */
    fun pollActive(): Boolean = inSession && now() - sessionStart < LINK_POLL_MAX_MS

    fun inLinkSession(): Boolean = inSession

    private fun inGrace(): Boolean = inSession && now() - sessionStart < LINK_GRACE_MS

    fun onAmazonHomeWindow(): Boolean {
        if (isPaused() || inGrace()) return false
        inSession = false
        return true
    }

    fun onLauncherFocus(viewId: String?): Boolean {
        if (!inSession || viewId != AMAZON_HOME_TAB_ID || inGrace() || isPaused()) return false
        inSession = false
        return true
    }
}
