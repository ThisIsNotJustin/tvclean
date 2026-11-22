package dev.tvclean.home.core

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RedirectPolicyTest {
    private var t = 0L
    private val policy = RedirectPolicy { t }

    @Test fun redirectsByDefault() {
        assertTrue(policy.onAmazonHomeWindow())
    }

    @Test fun pauseBlocksRedirect() {
        policy.startLinkSession()
        policy.pauseFor(30_000)
        assertFalse(policy.inLinkSession())
        t = 29_999
        assertTrue(policy.isPaused())
        assertFalse(policy.onAmazonHomeWindow())
        t = 30_000
        assertFalse(policy.isPaused())
        assertTrue(policy.onAmazonHomeWindow())
    }

    @Test fun linkGraceIgnoresLanding() {
        policy.startLinkSession()
        t = 2_499
        assertFalse(policy.onAmazonHomeWindow())
        assertTrue(policy.inLinkSession())
        t = 2_500
        assertTrue(policy.onAmazonHomeWindow())
        assertFalse(policy.inLinkSession())
    }

    @Test fun homeTabFocusAfterGraceRedirects() {
        policy.startLinkSession()
        t = 2_499
        assertFalse(policy.onLauncherFocus(AMAZON_HOME_TAB_ID))
        t = 2_500
        assertTrue(policy.onLauncherFocus(AMAZON_HOME_TAB_ID))
        assertFalse(policy.inLinkSession())
    }

    @Test fun renewGraceExtendsWindow() {
        policy.startLinkSession()
        t = 1_900
        policy.renewGrace()
        t = 4_399
        assertFalse(policy.onAmazonHomeWindow())
        t = 4_400
        assertTrue(policy.onAmazonHomeWindow())
    }

    @Test fun renewGraceOutsideSessionIsNoop() {
        policy.renewGrace()
        assertFalse(policy.inLinkSession())
        assertTrue(policy.onAmazonHomeWindow())
    }

    @Test fun focusOutsideSessionIgnored() {
        assertFalse(policy.onLauncherFocus(AMAZON_HOME_TAB_ID))
        policy.startLinkSession()
        t = 3_000
        assertFalse(policy.onLauncherFocus(null))
        assertFalse(policy.onLauncherFocus("some-tile"))
        assertTrue(policy.inLinkSession())
    }

    @Test fun pollActiveDuringSession() {
        assertFalse(policy.pollActive())
        policy.startLinkSession()
        t = 60_000
        assertTrue(policy.pollActive())
    }

    @Test fun pollStopsAfterCap() {
        policy.startLinkSession()
        t = 119_999
        assertTrue(policy.pollActive())
        t = 120_000
        assertFalse(policy.pollActive())
        policy.renewGrace()
        assertTrue(policy.pollActive())
    }

    @Test fun pollStopsWhenSessionEnds() {
        policy.startLinkSession()
        policy.pauseFor(1_000)
        assertFalse(policy.pollActive())
    }

    @Test fun inGraceReflectsWindow() {
        assertFalse(policy.inGrace())
        policy.startLinkSession()
        t = 2_499
        assertTrue(policy.inGrace())
        t = 2_500
        assertFalse(policy.inGrace())
    }

    @Test fun breakerPausesAfterThreeUnshownRedirects() {
        policy.onRedirect()
        t = 3_000
        policy.onRedirect()
        assertFalse(policy.isPaused())
        t = 6_000
        policy.onRedirect()
        assertTrue(policy.isPaused())
        assertFalse(policy.onAmazonHomeWindow())
        t = 6_000 + 299_999
        assertTrue(policy.isPaused())
        t = 6_000 + 300_000
        assertFalse(policy.isPaused())
    }

    @Test fun homeShownResetsBreaker() {
        policy.onRedirect()
        t = 1_000
        policy.onRedirect()
        policy.onHomeShown()
        t = 2_000
        policy.onRedirect()
        assertFalse(policy.isPaused())
    }

    @Test fun redirectsSpreadOutDontTrip() {
        policy.onRedirect()
        t = 6_000
        policy.onRedirect()
        t = 12_000
        policy.onRedirect()
        t = 18_000
        policy.onRedirect()
        assertFalse(policy.isPaused())
    }
}
