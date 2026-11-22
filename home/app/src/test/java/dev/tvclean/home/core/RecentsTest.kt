package dev.tvclean.home.core

import org.junit.Assert.assertEquals
import org.junit.Test

class RecentsTest {

    private val netflix = ResolvedApp("Netflix", "com.netflix.ninja", 0xFF000001)
    private val hulu = ResolvedApp("Hulu", "com.hulu.plus", 0xFF000002)
    private val disney = ResolvedApp("Disney+", "com.disney.disneyplus", 0xFF000003)
    private val prime = ResolvedApp("Prime Video", "com.amazon.firebat", 0xFF000004)
    private val apps = listOf(disney, hulu, prime, netflix)

    @Test
    fun ranksMostRecentFirst() {
        val events = listOf(
            UsageEvent("com.netflix.ninja", 100),
            UsageEvent("com.hulu.plus", 300),
            UsageEvent("com.netflix.ninja", 500),
            UsageEvent("com.disney.disneyplus", 200),
        )
        assertEquals(
            listOf(
                Slide(netflix, 500),
                Slide(hulu, 300),
                Slide(disney, 200),
            ),
            rankSlides(events, apps),
        )
    }

    @Test
    fun rankIgnoresUnresolvedApps() {
        val events = listOf(
            UsageEvent("com.amazon.tv.launcher", 900),
            UsageEvent("com.unknown.app", 800),
            UsageEvent("com.hulu.plus", 100),
        )
        assertEquals(
            listOf(
                Slide(hulu, 100),
                Slide(disney, null),
                Slide(prime, null),
            ),
            rankSlides(events, apps),
        )
    }

    @Test
    fun fillsFromCatalogWhenNoEvents() {
        assertEquals(
            listOf(
                Slide(disney, null),
                Slide(hulu, null),
                Slide(prime, null),
            ),
            rankSlides(emptyList(), apps),
        )
    }

    @Test
    fun fillsRowOrderAfterOneEvent() {
        val events = listOf(UsageEvent("com.netflix.ninja", 700))
        assertEquals(
            listOf(
                Slide(netflix, 700),
                Slide(disney, null),
                Slide(hulu, null),
            ),
            rankSlides(events, apps),
        )
    }

    @Test
    fun fewerAppsThanMax() {
        assertEquals(
            listOf(Slide(disney, null), Slide(hulu, null)),
            rankSlides(emptyList(), listOf(disney, hulu)),
        )
        assertEquals(emptyList<Slide>(), rankSlides(emptyList(), emptyList()))
    }

    @Test
    fun nonPositiveMaxGivesNoSlides() {
        assertEquals(emptyList<Slide>(), rankSlides(emptyList(), apps, max = 0))
    }

    @Test
    fun lastUsedText() {
        assertEquals(null, lastUsedText(null, 1_000_000L))
        assertEquals("Opened just now", lastUsedText(1_000_000L - 30_000L, 1_000_000L))
        assertEquals("Opened just now", lastUsedText(2_000_000L, 1_000_000L))
        assertEquals("Opened 12 min ago", lastUsedText(0L, 12 * 60_000L))
        assertEquals("Opened 3 h ago", lastUsedText(0L, 3 * 3_600_000L))
        assertEquals("Opened yesterday", lastUsedText(0L, 26 * 3_600_000L))
        assertEquals("Opened 4 days ago", lastUsedText(0L, 4 * 86_400_000L))
    }
}
