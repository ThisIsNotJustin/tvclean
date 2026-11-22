package dev.tvclean.home.core

import org.junit.Assert.assertEquals
import org.junit.Test

class AmazonLinksTest {
    @Test fun amazonUris() {
        assertEquals(
            "amzn://com.amazon.tv.launcher/menuNavigation?locationID=movies_and_tv_movies_tab",
            amazonUri(AmazonPage.MOVIES),
        )
        val expected = mapOf(
            AmazonPage.SEARCH to ("search_tab_v2" to true),
            AmazonPage.MOVIES to ("movies_and_tv_movies_tab" to true),
            AmazonPage.SHOWS to ("movies_and_tv_shows_tab" to true),
            AmazonPage.LIVE to ("movies_and_tv_guide_tab" to true),
            AmazonPage.SPORTS to ("movies_and_tv_sports_tab" to true),
            AmazonPage.NEWS to ("movies_and_tv_news_tab" to true),
            AmazonPage.INPUTS to ("inputs_destination" to false),
            AmazonPage.SETTINGS to ("settings_destination" to false),
        )
        assertEquals(AmazonPage.values().size, expected.size)
        for ((page, v) in expected) {
            assertEquals(v.first, page.locationId)
            assertEquals(v.second, page.needsAmazonHome)
        }
    }
}
