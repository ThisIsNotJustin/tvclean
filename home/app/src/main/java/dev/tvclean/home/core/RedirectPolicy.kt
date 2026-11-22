package dev.tvclean.home.core

/** Decides when Amazon Home appearing should send the owner back to our Home. True = redirect now. */
class RedirectPolicy(private val now: () -> Long) {
    private var pausedUntil = 0L
    private var inSession = false
    private var sessionStart = 0L

    private val redirects = ArrayDeque<Long>()

    /** A redirect to our Home was sent. Three within 10 s with no onHomeShown() means Home cannot come up: pause 5 min. */
    fun onRedirect() {
        val t = now()
        redirects.addLast(t)
        while (redirects.isNotEmpty() && t - redirects.first() >= BREAKER_WINDOW_MS) redirects.removeFirst()
        if (redirects.size >= BREAKER_COUNT) {
            redirects.clear()
            pauseFor(BREAKER_PAUSE_MS)
        }
    }

    /** Our Home reached the screen: it works, so forget earlier redirects. */
    fun onHomeShown() {
        redirects.clear()
    }

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

    /** True while a link session is still inside its grace window (nothing to look at yet). */
    fun inGrace(): Boolean = inSession && now() - sessionStart < LINK_GRACE_MS

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

    private companion object {
        const val BREAKER_WINDOW_MS = 10_000L
        const val BREAKER_COUNT = 3
        const val BREAKER_PAUSE_MS = 300_000L
    }
}
