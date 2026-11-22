package dev.tvclean.home

import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import dev.tvclean.home.core.AppCatalog
import dev.tvclean.home.core.ResolvedApp
import dev.tvclean.home.core.UsageEvent
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

/** Android-facing data for the home screen. Every suspend function runs off the main thread. */
class AppRepository(context: Context) {
    private val context = context.applicationContext
    private val pm = this.context.packageManager

    suspend fun loadApps(): List<ResolvedApp> = withContext(Dispatchers.IO) {
        val override = try {
            context.getExternalFilesDir(null)?.let { File(it, "apps.json") }
                ?.takeIf { it.isFile }?.readText()
        } catch (e: Exception) {
            null
        }
        val default = context.assets.open("apps.json").bufferedReader().use { it.readText() }
        AppCatalog.resolve(AppCatalog.parseOrDefault(override, default), ::isLaunchable)
    }

    suspend fun usageEvents(sinceMillis: Long): List<UsageEvent> = withContext(Dispatchers.IO) {
        try {
            val usm = context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
            val events = usm.queryEvents(sinceMillis, System.currentTimeMillis())
            val out = ArrayList<UsageEvent>()
            val event = UsageEvents.Event()
            while (events.hasNextEvent()) {
                events.getNextEvent(event)
                if (event.eventType == UsageEvents.Event.ACTIVITY_RESUMED) {
                    out += UsageEvent(event.packageName, event.timeStamp)
                }
            }
            out
        } catch (e: Exception) {
            emptyList()
        }
    }

    suspend fun banner(pkg: String, widthPx: Int, heightPx: Int): ImageBitmap? =
        withContext(Dispatchers.Default) {
            try {
                val banner = pm.getApplicationBanner(pkg)
                val drawable = banner ?: pm.getApplicationIcon(pkg)
                val bitmap = Bitmap.createBitmap(widthPx, heightPx, Bitmap.Config.ARGB_8888)
                val canvas = Canvas(bitmap)
                if (banner != null) {
                    drawable.setBounds(0, 0, widthPx, heightPx)
                } else {
                    // Square icon: centre it, keep the aspect ratio.
                    val left = (widthPx - heightPx) / 2
                    drawable.setBounds(left, 0, left + heightPx, heightPx)
                }
                drawable.draw(canvas)
                bitmap.asImageBitmap()
            } catch (e: Exception) {
                null
            }
        }

    fun launch(pkg: String): Boolean {
        val intent = launchIntent(pkg) ?: return false
        return try {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            true
        } catch (e: Exception) {
            false
        }
    }

    private fun launchIntent(pkg: String): Intent? =
        pm.getLeanbackLaunchIntentForPackage(pkg) ?: pm.getLaunchIntentForPackage(pkg)

    private fun isLaunchable(pkg: String): Boolean = try {
        launchIntent(pkg) != null && pm.getApplicationInfo(pkg, 0).enabled
    } catch (e: Exception) {
        false
    }
}
