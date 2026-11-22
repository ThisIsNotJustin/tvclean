package dev.tvclean.home.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.text.BasicText
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.tvclean.home.core.AmazonPage
import dev.tvclean.home.core.Carousel
import dev.tvclean.home.core.ResolvedApp
import dev.tvclean.home.core.Slide
import kotlinx.coroutines.delay

data class HomeUiState(
    val apps: List<ResolvedApp>,
    val slides: List<Slide>,
    val banners: Map<String, ImageBitmap>,
    val focusResetKey: Int,
    val menuOpen: Boolean,
)

class HomeActions(
    val launch: (String) -> Unit,
    val openPage: (AmazonPage) -> Unit,
    val openMenu: () -> Unit,
    val closeMenu: () -> Unit,
)

private const val TICK_MILLIS = 250L

@Composable
fun HomeScreen(state: HomeUiState, actions: HomeActions) {
    val listState = rememberLazyListState()
    val firstTile = remember { FocusRequester() }
    val carousel = remember(state.slides.size) { Carousel(state.slides.size) }
    val index = remember(carousel) { mutableIntStateOf(0) }
    val progress = remember(carousel) { mutableFloatStateOf(0f) }

    fun sync() {
        index.intValue = carousel.index
        progress.floatValue = carousel.progress
    }

    LaunchedEffect(carousel) {
        while (true) {
            delay(TICK_MILLIS)
            carousel.tick(TICK_MILLIS)
            sync()
        }
    }
    LaunchedEffect(state.focusResetKey, state.apps.isNotEmpty()) {
        carousel.reset()
        sync()
        listState.scrollToItem(0)
        try {
            firstTile.requestFocus()
        } catch (_: IllegalStateException) {
            // First tile not attached yet; the next reset or load retries.
        }
    }

    Box(Modifier.fillMaxSize().background(Background)) {
        Column(Modifier.fillMaxSize()) {
            Box(Modifier.fillMaxWidth().weight(0.62f)) {
                val slide = state.slides.getOrNull(index.intValue)
                if (slide != null) {
                    Hero(
                        slide = slide,
                        banner = state.banners[slide.app.packageName],
                        index = index.intValue,
                        count = state.slides.size,
                        progress = { progress.floatValue },
                        onLaunch = { actions.launch(slide.app.packageName) },
                        onButtonFocus = { carousel.setPaused(it) },
                        onPrevious = { carousel.previous(); sync() },
                        onNext = { carousel.next(); sync() },
                        modifier = Modifier.fillMaxSize(),
                    )
                }
                BasicText(
                    "YOUR APPS",
                    Modifier.align(Alignment.BottomStart).padding(start = Gutter, bottom = 4.dp),
                    style = textStyle(11.sp, TextPrimary.copy(alpha = 0.55f)),
                )
            }
            Box(Modifier.fillMaxWidth().weight(0.38f)) {
                AppRow(
                    apps = state.apps,
                    banners = state.banners,
                    listState = listState,
                    firstTile = firstTile,
                    launch = actions.launch,
                    openPage = actions.openPage,
                )
            }
        }
        NavPill(
            actions.openMenu,
            actions.openPage,
            Modifier.align(Alignment.TopCenter).padding(top = 20.dp),
        )
        Clock(Modifier.align(Alignment.TopEnd).padding(top = 28.dp, end = 32.dp))
    }
}
