package dev.tvclean.home.ui

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp

val Background = Color(0xFF05060A)
val TextPrimary = Color(0xFFF5F5F7)
val NavPillColor = Color(0x8C282C38)

val FocusScale = 1.1f
val FocusBorder = 2.dp

fun textStyle(size: TextUnit, color: Color = TextPrimary, weight: FontWeight = FontWeight.Normal) =
    TextStyle(color = color, fontSize = size, fontWeight = weight)

/**
 * Plain foundation focusable: scales via graphicsLayer (layer phase only), 2 dp white border when
 * focused. No shadow, no tv-material Surface.
 */
@Composable
fun FocusBox(
    onClick: () -> Unit,
    shape: Shape,
    modifier: Modifier = Modifier,
    background: Color = Color.Transparent,
    focusedBackground: Color = background,
    content: @Composable BoxScope.(focused: Boolean) -> Unit,
) {
    var focused by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(if (focused) FocusScale else 1f, tween(120), label = "focusScale")
    Box(
        modifier
            .graphicsLayer {
                scaleX = scale
                scaleY = scale
            }
            .onFocusChanged { focused = it.isFocused }
            .clip(shape)
            .background(if (focused) focusedBackground else background)
            .then(if (focused) Modifier.border(FocusBorder, Color.White, shape) else Modifier)
            .clickable(onClick = onClick),
    ) { content(focused) }
}

val Corner10 = RoundedCornerShape(10.dp)
val Gutter: Dp = 48.dp
