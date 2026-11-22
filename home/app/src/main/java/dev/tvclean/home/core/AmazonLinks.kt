package dev.tvclean.home.core

const val AMAZON_HOME_TAB_ID = "nav-tab-movies_and_tv_home_tab"
const val ESCAPE_PAUSE_MS = 30_000L
const val LINK_GRACE_MS = 2_500L
const val TAB_LINK_DELAY_MS = 800L

enum class AmazonPage(val locationId: String, val needsAmazonHome: Boolean) {
    SEARCH("search_tab_v2", true),
    MOVIES("movies_and_tv_movies_tab", true),
    SHOWS("movies_and_tv_shows_tab", true),
    LIVE("movies_and_tv_guide_tab", true),
    SPORTS("movies_and_tv_sports_tab", true),
    NEWS("movies_and_tv_news_tab", true),
    INPUTS("inputs_destination", false),
    SETTINGS("settings_destination", false),
}

fun amazonUri(page: AmazonPage): String =
    "amzn://com.amazon.tv.launcher/menuNavigation?locationID=${page.locationId}"
