package dev.tvclean.home.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.focus.onFocusChanged
import kotlinx.coroutines.launch
import androidx.compose.foundation.text.BasicText
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.tvclean.home.core.AmazonPage
import dev.tvclean.home.core.ResolvedApp

private val TileModifier = Modifier.size(152.dp, 86.dp)
private val InputsColor = Color(0xFF1D1D1F)

@Composable
fun AppRow(
    apps: List<ResolvedApp>,
    banners: Map<String, ImageBitmap>,
    listState: LazyListState,
    firstTile: FocusRequester,
    launch: (String) -> Unit,
    openPage: (AmazonPage) -> Unit,
    modifier: Modifier = Modifier,
) {
    val scope = rememberCoroutineScope()
    // Keep the focused tile aligned to the start padding so the scaled border is never cut off at
    // the screen edge.
    fun align(index: Int): Modifier = Modifier.onFocusChanged {
        if (it.isFocused) scope.launch { listState.animateScrollToItem(index) }
    }
    LazyRow(
        modifier,
        state = listState,
        contentPadding = PaddingValues(start = Gutter, end = Gutter, top = 12.dp, bottom = 12.dp),
        horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        itemsIndexed(apps, key = { _, app -> app.packageName }) { i, app ->
            val first = if (i == 0) Modifier.focusRequester(firstTile) else Modifier
            AppTile(app, banners[app.packageName], { launch(app.packageName) }, align(i).then(first))
        }
        item(key = "inputs") {
            val first = if (apps.isEmpty()) Modifier.focusRequester(firstTile) else Modifier
            FocusBox(
                onClick = { openPage(AmazonPage.INPUTS) },
                shape = Corner10,
                modifier = TileModifier.then(align(apps.size)).then(first),
                background = InputsColor,
            ) {
                Box(Modifier.fillMaxSize().padding(14.dp), contentAlignment = Alignment.CenterStart) {
                    androidx.compose.foundation.layout.Column {
                        BasicText("Inputs", style = textStyle(16.sp, weight = FontWeight.SemiBold))
                        BasicText(
                            "HDMI · Antenna",
                            Modifier.padding(top = 4.dp),
                            style = textStyle(11.sp, TextPrimary.copy(alpha = 0.6f)),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun AppTile(app: ResolvedApp, banner: ImageBitmap?, onClick: () -> Unit, modifier: Modifier) {
    FocusBox(
        onClick = onClick,
        shape = Corner10,
        modifier = TileModifier.then(modifier),
        background = Color(app.color),
    ) {
        if (banner != null) {
            Image(banner, app.label, Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
        } else {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                BasicText(app.label, style = textStyle(16.sp, Color.White, FontWeight.Bold))
            }
        }
    }
}
