package dev.tvclean.home

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.lifecycleScope
import dev.tvclean.home.core.rankSlides
import dev.tvclean.home.ui.HomeActions
import dev.tvclean.home.ui.HomeScreen
import dev.tvclean.home.ui.HomeUiState
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch

private const val BANNER_WIDTH_PX = 640
private const val BANNER_HEIGHT_PX = 360
private const val USAGE_WINDOW_MILLIS = 7L * 24 * 60 * 60 * 1000

class HomeActivity : ComponentActivity() {
    private lateinit var repo: AppRepository
    private var state by mutableStateOf(HomeUiState(emptyList(), emptyList(), emptyMap(), 0, false))
    private var loadJob: Job? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repo = AppRepository(this)
        SystemSwitches.ensureRedirectEnabled(this)

        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    if (state.menuOpen) state = state.copy(menuOpen = false)
                }
            },
        )

        val actions = HomeActions(
            launch = { repo.launch(it) },
            openPage = { AmazonNavigator.open(this, it) },
            openMenu = { state = state.copy(menuOpen = true) },
            closeMenu = { state = state.copy(menuOpen = false) },
        )
        setContent { HomeScreen(state, actions) }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        state = state.copy(menuOpen = false, focusResetKey = state.focusResetKey + 1)
    }

    override fun onResume() {
        super.onResume()
        loadJob?.cancel()
        loadJob = lifecycleScope.launch {
            val apps = repo.loadApps()
            val now = System.currentTimeMillis()
            val events = repo.usageEvents(now - USAGE_WINDOW_MILLIS)
            val kept = state.banners.filterKeys { pkg -> apps.any { it.packageName == pkg } }
            state = state.copy(apps = apps, slides = rankSlides(events, apps), banners = kept)

            val loaded = HashMap(kept)
            for (app in apps) {
                if (app.packageName in loaded) continue
                repo.banner(app.packageName, BANNER_WIDTH_PX, BANNER_HEIGHT_PX)
                    ?.let { loaded[app.packageName] = it }
            }
            if (loaded.size != kept.size) state = state.copy(banners = loaded)
        }
    }
}
