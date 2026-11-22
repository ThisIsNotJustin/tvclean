package dev.tvclean.home.core

import org.junit.Assert.assertEquals
import org.junit.Test

class CarouselTest {

    @Test
    fun carouselAdvancesAfter15s() {
        val carousel = Carousel(size = 3)
        carousel.tick(14_999)
        assertEquals(0, carousel.index)
        carousel.tick(1)
        assertEquals(1, carousel.index)
        assertEquals(0f, carousel.progress, 0f)
        carousel.tick(15_000)
        assertEquals(2, carousel.index)
        carousel.tick(15_000)
        assertEquals(0, carousel.index)
    }

    @Test
    fun carouselPausedDoesNotAdvance() {
        val carousel = Carousel(size = 3)
        carousel.tick(7_500)
        val progressBefore = carousel.progress
        carousel.setPaused(true)
        carousel.tick(60_000)
        assertEquals(0, carousel.index)
        assertEquals(progressBefore, carousel.progress, 0f)
        carousel.setPaused(false)
        carousel.tick(7_500)
        assertEquals(1, carousel.index)
    }

    @Test
    fun carouselProgress() {
        val carousel = Carousel(size = 3)
        carousel.tick(7_500)
        assertEquals(0.5f, carousel.progress, 0f)
    }

    @Test
    fun carouselLargeTickAdvancesWholeSlides() {
        val carousel = Carousel(size = 3)
        carousel.tick(40_000)
        assertEquals(2, carousel.index)
        assertEquals(10_000f / 15_000f, carousel.progress, 1e-6f)
    }

    @Test
    fun carouselSelectAndStep() {
        val carousel = Carousel(size = 3)
        carousel.tick(7_500)
        carousel.select(2)
        assertEquals(2, carousel.index)
        assertEquals(0f, carousel.progress, 0f)
        carousel.next()
        assertEquals(0, carousel.index)
        carousel.previous()
        assertEquals(2, carousel.index)
        carousel.tick(5_000)
        carousel.reset()
        assertEquals(0, carousel.index)
        assertEquals(0f, carousel.progress, 0f)
    }

    @Test
    fun carouselSelectOutOfRangeIsIgnored() {
        val carousel = Carousel(size = 3)
        carousel.select(1)
        carousel.select(3)
        carousel.select(-1)
        assertEquals(1, carousel.index)
    }

    @Test
    fun carouselWithOneSlideNeverAdvances() {
        val one = Carousel(size = 1)
        one.tick(100_000)
        assertEquals(0, one.index)
        one.next()
        one.previous()
        assertEquals(0, one.index)
    }

    @Test
    fun carouselWithNoSlidesNeverAdvances() {
        val none = Carousel(size = 0)
        none.tick(100_000)
        assertEquals(0, none.index)
        none.next()
        none.previous()
        assertEquals(0, none.index)
    }
}
