package dev.tvclean.home.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicText
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import dev.tvclean.home.core.AmazonPage

private val PillShape = RoundedCornerShape(50)
private val ItemShape = RoundedCornerShape(50)
private val CurrentBackground = Color.White.copy(alpha = 0.18f)

private class NavItem(val label: String, val page: AmazonPage?)

private val items = listOf(
    NavItem("Search", AmazonPage.SEARCH),
    NavItem("Home", null),
    NavItem("Movies", AmazonPage.MOVIES),
    NavItem("TV Shows", AmazonPage.SHOWS),
    NavItem("Live", AmazonPage.LIVE),
    NavItem("Sports", AmazonPage.SPORTS),
    NavItem("News", AmazonPage.NEWS),
)

@Composable
fun NavPill(
    openMenu: () -> Unit,
    openPage: (AmazonPage) -> Unit,
    menuButton: FocusRequester,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier
            .background(NavPillColor, PillShape)
            .padding(horizontal = 8.dp, vertical = 6.dp),
        horizontalArrangement = Arrangement.spacedBy(2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        FocusBox(
            onClick = openMenu,
            shape = ItemShape,
            modifier = Modifier.focusRequester(menuButton),
            focusedBackground = Color.White,
        ) { focused ->
            Column(
                Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                verticalArrangement = Arrangement.spacedBy(3.dp),
            ) {
                repeat(3) {
                    Box(
                        Modifier
                            .width(14.dp)
                            .height(2.dp)
                            .background(if (focused) Color.Black else TextPrimary),
                    )
                }
            }
        }
        for (item in items) {
            val current = item.page == null
            FocusBox(
                onClick = { item.page?.let(openPage) },
                shape = ItemShape,
                background = if (current) CurrentBackground else Color.Transparent,
                focusedBackground = Color.White,
            ) { focused ->
                BasicText(
                    item.label,
                    Modifier.padding(horizontal = 14.dp, vertical = 7.dp),
                    style = textStyle(13.sp, if (focused) Color.Black else TextPrimary),
                )
            }
        }
    }
}
