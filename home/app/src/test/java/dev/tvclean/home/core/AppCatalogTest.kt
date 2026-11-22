package dev.tvclean.home.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import java.io.File

class AppCatalogTest {

    private val defaultJson: String
        get() = File("src/main/assets/apps.json").readText()

    private fun appsJson(vararg entries: String, version: Int = 1): String =
        """{"version":$version,"apps":[${entries.joinToString(",")}]}"""

    private fun entry(
        label: String = "Test",
        packages: String = "\"com.test.app\"",
        color: String = "\"#112233\"",
    ): String = """{"label":"$label","packages":[$packages],"color":$color}"""

    @Test
    fun parsesBundledDefault() {
        val apps = AppCatalog.parse(defaultJson)
        assertEquals(9, apps.size)
        assertEquals(
            AppEntry("Disney+", listOf("com.disney.disneyplus"), 0xFF1B4FBF),
            apps.first(),
        )
        assertEquals(
            listOf("com.wbd.stream", "com.hbo.hbonow"),
            apps.first { it.label == "HBO Max" }.packages,
        )
    }

    @Test
    fun rejectsBadVersion() {
        assertThrows(CatalogException::class.java) {
            AppCatalog.parse(appsJson(entry(), version = 2))
        }
    }

    @Test
    fun rejectsBadColor() {
        assertThrows(CatalogException::class.java) {
            AppCatalog.parse(appsJson(entry(color = "\"blue\"")))
        }
    }

    @Test
    fun rejectsEmptyPackages() {
        assertThrows(CatalogException::class.java) {
            AppCatalog.parse(appsJson(entry(packages = "")))
        }
    }

    @Test
    fun rejectsBlankLabel() {
        assertThrows(CatalogException::class.java) {
            AppCatalog.parse(appsJson(entry(label = "  ")))
        }
    }

    @Test
    fun rejectsEmptyApps() {
        assertThrows(CatalogException::class.java) {
            AppCatalog.parse("""{"version":1,"apps":[]}""")
        }
    }

    @Test
    fun invalidOverrideFallsBack() {
        val default = AppCatalog.parse(defaultJson)
        assertEquals(default, AppCatalog.parseOrDefault("{not json", defaultJson))
        assertEquals(default, AppCatalog.parseOrDefault("", defaultJson))
        assertEquals(default, AppCatalog.parseOrDefault(null, defaultJson))
    }

    @Test
    fun validOverrideIsUsed() {
        val override = appsJson(entry(label = "Only", packages = "\"com.only.app\""))
        assertEquals(
            listOf(AppEntry("Only", listOf("com.only.app"), 0xFF112233)),
            AppCatalog.parseOrDefault(override, defaultJson),
        )
    }

    @Test
    fun resolveSkipsMissing() {
        val apps = AppCatalog.parse(defaultJson)
        val launchable = setOf("com.hulu.plus", "com.hbo.hbonow")
        assertEquals(
            listOf(
                ResolvedApp("Hulu", "com.hulu.plus", 0xFF1CE783),
                ResolvedApp("HBO Max", "com.hbo.hbonow", 0xFF5B2BE0),
            ),
            AppCatalog.resolve(apps) { it in launchable },
        )
    }

    @Test
    fun resolveUsesFirstLaunchablePackage() {
        val apps = AppCatalog.parse(defaultJson)
        val launchable = setOf("com.wbd.stream", "com.hbo.hbonow")
        assertEquals(
            "com.wbd.stream",
            AppCatalog.resolve(apps) { it in launchable }.single().packageName,
        )
    }
}
