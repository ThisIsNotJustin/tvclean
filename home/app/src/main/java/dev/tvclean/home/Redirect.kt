package dev.tvclean.home

import android.os.SystemClock
import dev.tvclean.home.core.RedirectPolicy

/** Process-wide state shared by the accessibility service and the activity. */
object Redirect {
    val policy = RedirectPolicy { SystemClock.uptimeMillis() }

    /** Set by RedirectService so it can adjust its event subscription when a session starts or ends. */
    var onSessionChange: (() -> Unit)? = null
}
