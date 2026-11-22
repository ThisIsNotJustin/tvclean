package dev.tvclean.home.core

import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

data class AppEntry(val label: String, val packages: List<String>, val color: Long)

data class ResolvedApp(val label: String, val packageName: String, val color: Long)

class CatalogException(message: String) : Exception(message)

/**
 * App order and labels for the home row. Pure Kotlin: no android.* imports.
 *
 * JSON schema: {"version": 1, "apps": [{"label": str, "packages": [str, ...], "color": "#RRGGBB"}]}
 */
object AppCatalog {
    private const val VERSION = 1
    private val COLOR_PATTERN = Regex("^#[0-9A-Fa-f]{6}$")

    fun parse(json: String): List<AppEntry> {
        try {
            val root = JSONObject(json)
            if (root.opt("version") != VERSION) {
                throw CatalogException("unsupported catalog version")
            }
            val apps = root.optJSONArray("apps")
                ?: throw CatalogException("missing apps array")
            if (apps.length() == 0) throw CatalogException("empty apps array")
            return (0 until apps.length()).map { parseEntry(apps.getJSONObject(it)) }
        } catch (e: JSONException) {
            throw CatalogException("invalid catalog JSON: ${e.message}")
        }
    }

    fun parseOrDefault(override: String?, default: String): List<AppEntry> {
        if (!override.isNullOrBlank()) {
            try {
                return parse(override)
            } catch (_: CatalogException) {
                // Fall through to the bundled default.
            }
        }
        return parse(default)
    }

    fun resolve(entries: List<AppEntry>, isLaunchable: (String) -> Boolean): List<ResolvedApp> =
        entries.mapNotNull { entry ->
            entry.packages.firstOrNull(isLaunchable)?.let { ResolvedApp(entry.label, it, entry.color) }
        }

    private fun parseEntry(obj: JSONObject): AppEntry {
        val label = obj.opt("label") as? String
        if (label.isNullOrBlank()) throw CatalogException("blank label")

        val packagesJson = obj.optJSONArray("packages") ?: throw CatalogException("missing packages")
        val packages = parsePackages(packagesJson)

        val color = obj.opt("color") as? String
        if (color == null || !COLOR_PATTERN.matches(color)) {
            throw CatalogException("bad color for $label")
        }
        return AppEntry(label, packages, color.substring(1).toLong(16) or 0xFF000000L)
    }

    private fun parsePackages(array: JSONArray): List<String> {
        if (array.length() == 0) throw CatalogException("empty packages")
        return (0 until array.length()).map { i ->
            val pkg = array.opt(i) as? String
            if (pkg.isNullOrBlank()) throw CatalogException("blank package name")
            pkg
        }
    }
}
