package dev.tvclean.home

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.SystemClock

/** After boot, makes sure the redirect service is enabled, retrying twice in case Settings was not ready. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        SystemSwitches.ensureRedirectEnabled(context)
        val alarms = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val now = SystemClock.elapsedRealtime()
        for ((i, delay) in listOf(30_000L, 90_000L).withIndex()) {
            val heal = Intent(HealReceiver.ACTION)
                .setComponent(ComponentName(context, HealReceiver::class.java))
            val pi = PendingIntent.getBroadcast(context, i, heal, PendingIntent.FLAG_IMMUTABLE)
            alarms.set(AlarmManager.ELAPSED_REALTIME, now + delay, pi)
        }
    }
}

/** Not exported: only reachable through the explicit-component PendingIntents set by BootReceiver. */
class HealReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == ACTION) SystemSwitches.ensureRedirectEnabled(context)
    }

    companion object {
        const val ACTION = "dev.tvclean.home.HEAL"
    }
}
