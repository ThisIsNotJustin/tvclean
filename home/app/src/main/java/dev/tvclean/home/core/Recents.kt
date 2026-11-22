package dev.tvclean.home.core

data class UsageEvent(val packageName: String, val timeMillis: Long)

/** A hero slide. [lastUsedMillis] is null for a filler taken from row order. */
data class Slide(val app: ResolvedApp, val lastUsedMillis: Long?)

private const val MINUTE_MILLIS = 60_000L
private const val HOUR_MILLIS = 60 * MINUTE_MILLIS
private const val DAY_MILLIS = 24 * HOUR_MILLIS

/**
 * Ranks apps by most recent use, then fills the remaining slots from [apps] in row order.
 * Events for packages not in [apps] are ignored.
 */
fun rankSlides(events: List<UsageEvent>, apps: List<ResolvedApp>, max: Int = 3): List<Slide> {
    if (max <= 0) return emptyList()
    val byPackage = apps.associateBy { it.packageName }
    val lastUsed = events
        .filter { it.packageName in byPackage }
        .groupBy { it.packageName }
        .mapValues { (_, list) -> list.maxOf { it.timeMillis } }
    val used = lastUsed.entries
        .sortedByDescending { it.value }
        .map { (packageName, time) -> Slide(byPackage.getValue(packageName), time) }
    val fillers = apps
        .filter { it.packageName !in lastUsed }
        .map { Slide(it, null) }
    return (used + fillers).take(max)
}

/** Human-readable "last opened" text, or null when the app was never used. */
fun lastUsedText(lastUsedMillis: Long?, nowMillis: Long): String? {
    if (lastUsedMillis == null) return null
    val diff = nowMillis - lastUsedMillis
    return when {
        diff < MINUTE_MILLIS -> "Opened just now"
        diff < HOUR_MILLIS -> "Opened ${diff / MINUTE_MILLIS} min ago"
        diff < DAY_MILLIS -> "Opened ${diff / HOUR_MILLIS} h ago"
        diff < 2 * DAY_MILLIS -> "Opened yesterday"
        else -> "Opened ${diff / DAY_MILLIS} days ago"
    }
}
