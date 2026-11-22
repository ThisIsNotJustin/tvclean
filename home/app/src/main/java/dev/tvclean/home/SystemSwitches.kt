package dev.tvclean.home

import android.content.Context
import android.content.pm.PackageManager
import android.provider.Settings

object SystemSwitches {
    const val SERVICE = "dev.tvclean.home/dev.tvclean.home.RedirectService"
    private const val ENABLED_SERVICES = "enabled_accessibility_services"
    private const val ACCESSIBILITY_ENABLED = "accessibility_enabled"
    /** Owner intent, written by `tvclean home on|off`: "0" means the owner turned the redirect off. */
    private const val REDIRECT_INTENT = "tvclean_home_redirect"
    private const val VOICE_DISABLED = "voice_disabled"

    private fun enabledList(context: Context): List<String> {
        val raw = Settings.Secure.getString(context.contentResolver, ENABLED_SERVICES)
        if (raw.isNullOrEmpty() || raw == "null") return emptyList()
        return raw.split(":").filter { it.isNotEmpty() }
    }

    fun isRedirectEnabled(context: Context): Boolean =
        SERVICE in enabledList(context) &&
            Settings.Secure.getInt(context.contentResolver, ACCESSIBILITY_ENABLED, 0) == 1

    /** Turns the redirect service on. False when the owner turned it off or WRITE_SECURE_SETTINGS has not been granted. */
    fun ensureRedirectEnabled(context: Context): Boolean {
        val cr = context.contentResolver
        return try {
            if (Settings.Secure.getString(cr, REDIRECT_INTENT) == "0") return false
            val list = enabledList(context)
            if (SERVICE !in list) {
                Settings.Secure.putString(cr, ENABLED_SERVICES, (list + SERVICE).joinToString(":"))
            }
            if (Settings.Secure.getInt(cr, ACCESSIBILITY_ENABLED, 0) != 1) {
                Settings.Secure.putInt(cr, ACCESSIBILITY_ENABLED, 1)
            }
            true
        } catch (e: SecurityException) {
            false
        }
    }

    fun alexaVoiceOn(context: Context): Boolean =
        Settings.Secure.getString(context.contentResolver, VOICE_DISABLED) != "1"

    fun setAlexaVoice(context: Context, on: Boolean): Boolean = try {
        Settings.Secure.putString(context.contentResolver, VOICE_DISABLED, if (on) "0" else "1")
        true
    } catch (e: SecurityException) {
        false
    }

    fun packageEnabled(context: Context, pkg: String): Boolean = try {
        when (context.packageManager.getApplicationEnabledSetting(pkg)) {
            PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
            PackageManager.COMPONENT_ENABLED_STATE_DISABLED_USER,
            PackageManager.COMPONENT_ENABLED_STATE_DISABLED_UNTIL_USED -> false
            else -> true
        }
    } catch (e: IllegalArgumentException) {
        false
    } catch (e: PackageManager.NameNotFoundException) {
        false
    }
}
