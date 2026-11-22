package dev.tvclean.home.ui

import android.content.Context
import android.content.pm.PackageManager
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.MutableTransitionState
import androidx.compose.animation.slideInHorizontally
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicText
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.withFrameNanos
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Popup
import androidx.compose.ui.window.PopupProperties
import dev.tvclean.home.SystemSwitches
import dev.tvclean.home.core.AmazonPage

private val PanelColor = Color(0xFF101216)
private val ScrimColor = Color(0x66000000)
private val PanelWidth = 320.dp
private val SwitchShape = RoundedCornerShape(13.dp)
private const val AIRPLAY_PKG = "com.apple.airplay.amazon.airplay"
private const val UPDATES_PKG = "com.amazon.tv.forcedotaupdater.v2"

/**
 * The ☰ menu: a 40% scrim over the screen and a 320 dp panel sliding in from the left. It is a
 * focusable popup, so D-pad focus stays in the menu window and cannot reach the screen behind it.
 * Status values are read each time the menu opens.
 */
@Composable
fun HomeMenu(open: Boolean, actions: HomeActions, firstItem: FocusRequester) {
    if (!open) return
    Popup(
        onDismissRequest = actions.closeMenu,
        properties = PopupProperties(focusable = true),
    ) {
        val visibleState = remember { MutableTransitionState(false) }
        LaunchedEffect(Unit) { visibleState.targetState = true }
        Box(Modifier.fillMaxSize().background(ScrimColor)) {
            AnimatedVisibility(
                visibleState = visibleState,
                enter = slideInHorizontally { -it },
            ) {
                MenuPanel(actions, firstItem)
            }
        }
    }
}

@Composable
private fun MenuPanel(actions: HomeActions, firstItem: FocusRequester) {
    val context = LocalContext.current
    var alexaOn by remember { mutableStateOf(SystemSwitches.alexaVoiceOn(context)) }
    var alexaDenied by remember { mutableStateOf(false) }
    var settingsFocused by remember { mutableStateOf(false) }
    val airplayOn = remember { SystemSwitches.packageEnabled(context, AIRPLAY_PKG) }
    val updatesOn = remember { SystemSwitches.packageEnabled(context, UPDATES_PKG) }
    val redirectOn = remember { SystemSwitches.isRedirectEnabled(context) }
    val version = remember { versionName(context) }

    LaunchedEffect(Unit) { firstItem.requestFocusUntil { settingsFocused } }

    Column(
        Modifier
            .width(PanelWidth)
            .fillMaxHeight()
            .background(PanelColor)
            .padding(horizontal = 20.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        BasicText(
            "tvclean",
            Modifier.padding(start = 12.dp, bottom = 12.dp),
            style = textStyle(24.sp, weight = FontWeight.SemiBold),
        )
        MenuItem(
            "Settings",
            onClick = { actions.closeMenu(); actions.openPage(AmazonPage.SETTINGS) },
            modifier = Modifier
                .focusRequester(firstItem)
                .onFocusChanged { if (it.isFocused) settingsFocused = true },
        )
        MenuItem("Inputs", onClick = { actions.closeMenu(); actions.openPage(AmazonPage.INPUTS) })
        MenuItem(
            "Amazon Home",
            onClick = { actions.closeMenu(); actions.openAmazonHome() },
            subtitle = "Opens Amazon's Home for 30 seconds",
        )
        MenuItem(
            "Alexa voice",
            onClick = {
                if (SystemSwitches.setAlexaVoice(context, !alexaOn)) {
                    alexaOn = SystemSwitches.alexaVoiceOn(context)
                    alexaDenied = false
                } else {
                    alexaDenied = true
                }
            },
            subtitle = if (alexaDenied) "Allow from your Mac: tvclean home install" else null,
            trailing = { focused -> SwitchKnob(alexaOn, focused) },
        )
        MenuItem(
            "AirPlay",
            onClick = {},
            subtitle = "Change from your Mac: tvclean feature airplay on|off",
            trailing = { focused -> StateText(airplayOn, focused) },
        )
        MenuItem(
            "Amazon updates",
            onClick = {},
            subtitle = "Change from your Mac: tvclean feature updates on|off",
            trailing = { focused -> StateText(updatesOn, focused) },
        )
        MenuItem(
            "About tvclean Home",
            onClick = {},
            subtitle = "Version $version\nHome button redirect: ${if (redirectOn) "On" else "Off"}",
        )
    }
}

@Composable
private fun MenuItem(
    title: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    trailing: (@Composable (focused: Boolean) -> Unit)? = null,
) {
    FocusBox(
        onClick = onClick,
        shape = Corner10,
        modifier = modifier.fillMaxWidth(),
        focusedBackground = Color.White,
    ) { focused ->
        val ink = if (focused) Color.Black else TextPrimary
        Row(
            Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                BasicText(title, style = textStyle(16.sp, ink, FontWeight.SemiBold))
                if (subtitle != null) {
                    BasicText(
                        subtitle,
                        Modifier.padding(top = 2.dp),
                        style = textStyle(12.sp, ink.copy(alpha = 0.7f)),
                    )
                }
            }
            if (trailing != null) {
                Spacer(Modifier.width(12.dp))
                trailing(focused)
            }
        }
    }
}

@Composable
private fun SwitchKnob(on: Boolean, focused: Boolean) {
    val track = when {
        focused && on -> Color.Black
        focused -> Color.Black.copy(alpha = 0.3f)
        on -> TextPrimary
        else -> TextPrimary.copy(alpha = 0.3f)
    }
    val knob = if (focused) Color.White else Background
    Box(Modifier.size(width = 48.dp, height = 26.dp).background(track, SwitchShape).padding(3.dp)) {
        Box(
            Modifier
                .align(if (on) Alignment.CenterEnd else Alignment.CenterStart)
                .size(20.dp)
                .background(knob, CircleShape),
        )
    }
}

@Composable
private fun StateText(on: Boolean, focused: Boolean) {
    BasicText(
        if (on) "On" else "Off",
        style = textStyle(14.sp, if (focused) Color.Black else TextPrimary, FontWeight.SemiBold),
    )
}

/**
 * Focus requests can be dropped while a window or panel is still settling, and they do not always
 * throw. Keep asking for a few frames until [landed] reports success.
 */
internal suspend fun FocusRequester.requestFocusUntil(frames: Int = 30, landed: () -> Boolean = { false }) {
    repeat(frames) {
        if (landed()) return
        try {
            requestFocus()
        } catch (_: IllegalStateException) {
            // Not attached yet; try again on the next frame.
        }
        withFrameNanos { }
    }
}

private fun versionName(context: Context): String = try {
    context.packageManager.getPackageInfo(context.packageName, 0).versionName ?: "unknown"
} catch (e: PackageManager.NameNotFoundException) {
    "unknown"
}
