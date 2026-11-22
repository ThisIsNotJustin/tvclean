package dev.tvclean.home.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicText
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.input.key.Key
import androidx.compose.ui.input.key.KeyEventType
import androidx.compose.ui.input.key.key
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.input.key.type
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.tvclean.home.core.Slide
import dev.tvclean.home.core.lastUsedText
import java.util.Locale

private val ButtonShape = RoundedCornerShape(50)

@Composable
fun Hero(
    slide: Slide,
    banner: ImageBitmap?,
    index: Int,
    count: Int,
    progress: () -> Float,
    onLaunch: () -> Unit,
    onButtonFocus: (Boolean) -> Unit,
    onPrevious: () -> Unit,
    onNext: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val app = slide.app
    val recent = slide.lastUsedMillis != null
    val meta = remember(slide) { lastUsedText(slide.lastUsedMillis, System.currentTimeMillis()) }
    val top = remember(app.color) { lerp(Color(app.color), Color.Black, 0.45f) }

    Box(modifier.background(Brush.verticalGradient(listOf(top, Background)))) {
        if (banner != null) {
            Image(
                banner, app.label,
                Modifier
                    .align(Alignment.CenterEnd)
                    .padding(end = Gutter)
                    .size(320.dp, 180.dp)
                    .clip(RoundedCornerShape(16.dp)),
                contentScale = ContentScale.Crop,
            )
        }
        Box(
            Modifier.fillMaxSize().background(
                Brush.horizontalGradient(0f to Background.copy(alpha = 0.85f), 0.55f to Color.Transparent),
            ),
        )
        Box(
            Modifier.fillMaxSize().background(
                Brush.verticalGradient(0.6f to Color.Transparent, 1f to Background),
            ),
        )
        Column(
            Modifier.align(Alignment.CenterStart).padding(start = Gutter, top = 40.dp),
        ) {
            BasicText(
                if (recent) "CONTINUE ON ${app.label.uppercase(Locale.ROOT)}" else "YOUR APPS",
                style = textStyle(12.sp, TextPrimary.copy(alpha = 0.8f), FontWeight.Medium),
            )
            BasicText(
                app.label,
                Modifier.padding(top = 6.dp),
                style = textStyle(44.sp, weight = FontWeight.Bold),
            )
            if (meta != null) {
                BasicText(
                    meta,
                    Modifier.padding(top = 4.dp),
                    style = textStyle(14.sp, TextPrimary.copy(alpha = 0.7f)),
                )
            }
            FocusBox(
                onClick = onLaunch,
                shape = ButtonShape,
                modifier = Modifier
                    .padding(top = 18.dp)
                    .heroKeys(onPrevious, onNext)
                    .onFocusChanged { onButtonFocus(it.isFocused) },
                background = Color.White,
            ) {
                BasicText(
                    if (recent) "▶ Resume" else "▶ Open",
                    Modifier.padding(horizontal = 22.dp, vertical = 9.dp),
                    style = textStyle(14.sp, Color.Black, FontWeight.SemiBold),
                )
            }
        }
        Dots(
            index, count, progress,
            Modifier.align(Alignment.BottomEnd).padding(end = Gutter, bottom = 12.dp),
        )
    }
}

@Composable
private fun Dots(index: Int, count: Int, progress: () -> Float, modifier: Modifier) {
    if (count < 2) return
    Row(modifier, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        repeat(count) { i ->
            val current = i == index
            Box(
                Modifier
                    .height(6.dp)
                    .width(if (current) 28.dp else 6.dp)
                    .drawBehind {
                        val r = CornerRadius(size.height / 2)
                        drawRoundRect(Color.White.copy(alpha = 0.35f), cornerRadius = r)
                        if (current) {
                            drawRoundRect(
                                Color.White,
                                size = Size(size.width * progress().coerceIn(0f, 1f), size.height),
                                cornerRadius = r,
                            )
                        }
                    },
            )
        }
    }
}

/** While the hero button is focused, D-pad Left/Right pages the carousel. */
private fun Modifier.heroKeys(onPrevious: () -> Unit, onNext: () -> Unit): Modifier =
    onPreviewKeyEvent { e ->
        when {
            e.key == Key.DirectionLeft -> { if (e.type == KeyEventType.KeyDown) onPrevious(); true }
            e.key == Key.DirectionRight -> { if (e.type == KeyEventType.KeyDown) onNext(); true }
            else -> false
        }
    }
