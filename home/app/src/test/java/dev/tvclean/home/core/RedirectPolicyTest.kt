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

    @Test fun homeTabFocusAfterArmingRedirects() {
        policy.startLinkSession()
        t = 500
        assertFalse(policy.onLauncherFocus(AMAZON_HOME_TAB_ID))
        t = 1_000
        assertFalse(policy.onLauncherFocus("some-tile"))
        t = 3_000
        assertTrue(policy.onLauncherFocus(AMAZON_HOME_TAB_ID))
        assertFalse(policy.inLinkSession())
    }

    @Test fun homeTabFocusInsideGraceIgnored() {
        policy.startLinkSession()
        t = 100
        assertFalse(policy.onLauncherFocus("some-tile"))
        t = 2_000
        assertFalse(policy.onLauncherFocus(AMAZON_HOME_TAB_ID))
        assertTrue(policy.inLinkSession())
    }

    @Test fun focusOutsideSessionIgnored() {
        assertFalse(policy.onLauncherFocus(AMAZON_HOME_TAB_ID))
        policy.startLinkSession()
        t = 1_000
        assertFalse(policy.onLauncherFocus(null))
        t = 5_000
        assertFalse(policy.onLauncherFocus(AMAZON_HOME_TAB_ID))
    }
}
