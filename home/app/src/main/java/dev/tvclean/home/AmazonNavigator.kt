package dev.tvclean.home

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Handler
import android.os.Looper
import android.util.Log
import dev.tvclean.home.core.AmazonPage
import dev.tvclean.home.core.ESCAPE_PAUSE_MS
import dev.tvclean.home.core.TAB_LINK_DELAY_MS
import dev.tvclean.home.core.amazonUri

object AmazonNavigator {
    private const val TAG = "TVHOME"
    private const val AMAZON_PKG = "com.amazon.tv.launcher"

    fun open(context: Context, page: AmazonPage) {
        val app = context.applicationContext
        Redirect.policy.startLinkSession()
        Redirect.onSessionChange?.invoke()
        try {
            if (page.needsAmazonHome) {
                app.startActivity(amazonHomeIntent())
                Handler(Looper.getMainLooper()).postDelayed({
                    try {
                        Redirect.policy.renewGrace()
                        Redirect.onSessionChange?.invoke()
                        app.startActivity(linkIntent(page))
                    } catch (e: ActivityNotFoundException) {
                        fallback(app, page, e)
                    } catch (e: SecurityException) {
                        fallback(app, page, e)
                    }
                }, TAB_LINK_DELAY_MS)
            } else {
                app.startActivity(linkIntent(page))
            }
        } catch (e: ActivityNotFoundException) {
            fallback(app, page, e)
        } catch (e: SecurityException) {
            fallback(app, page, e)
        }
    }

    /** Escape hatch: Amazon's own Home, with our redirect paused so it stays put. */
    fun openAmazonHome(context: Context) {
        Redirect.policy.pauseFor(ESCAPE_PAUSE_MS)
        Redirect.onSessionChange?.invoke()
        try {
            context.applicationContext.startActivity(amazonHomeIntent())
        } catch (e: ActivityNotFoundException) {
            Log.i(TAG, "Amazon Home failed (${e.javaClass.simpleName})")
        } catch (e: SecurityException) {
            Log.i(TAG, "Amazon Home failed (${e.javaClass.simpleName})")
        }
    }

    private fun fallback(context: Context, page: AmazonPage, e: Exception) {
        Log.i(TAG, "link ${page.locationId} failed (${e.javaClass.simpleName}); opening Amazon Home")
        openAmazonHome(context)
    }

    private fun amazonHomeIntent() = Intent(Intent.ACTION_MAIN)
        .addCategory(Intent.CATEGORY_HOME)
        .setPackage(AMAZON_PKG)
        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

    private fun linkIntent(page: AmazonPage) = Intent(Intent.ACTION_VIEW, Uri.parse(amazonUri(page)))
        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
}
