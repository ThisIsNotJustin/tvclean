package dev.tvclean.home.core

/**
 * Hero carousel state. Advances one slide every [slideMillis] unless paused.
 * With fewer than two slides it never advances.
 */
class Carousel(val size: Int, val slideMillis: Long = 15_000L) {

    var index: Int = 0
        private set

    /** Elapsed fraction of the current slide, in [0, 1). */
    var progress: Float = 0f
        private set

    private var elapsedInSlide = 0L
    private var paused = false

    fun tick(elapsedMillis: Long) {
        if (paused || size <= 1) return
        val total = elapsedInSlide + elapsedMillis
        val steps = total / slideMillis
        elapsedInSlide = total % slideMillis
        index = ((index + steps) % size).toInt()
        progress = elapsedInSlide.toFloat() / slideMillis
    }

    fun setPaused(paused: Boolean) {
        this.paused = paused
    }

    /** Jumps to [index]; out-of-range values are ignored. */
    fun select(index: Int) {
        if (index !in 0 until size) return
        this.index = index
        elapsedInSlide = 0L
        progress = 0f
    }

    fun next() {
        if (size > 0) select((index + 1) % size)
    }

    fun previous() {
        if (size > 0) select((index - 1 + size) % size)
    }

    fun reset() {
        select(0)
    }
}
