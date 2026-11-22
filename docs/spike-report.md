# Phase 2a spike report: can our own home screen work on this TV?

Date: 2026-11-22. TV: Insignia NS75-UQFL26, Fire OS 8.1.8.5 (RS8185/3898), with the Phase 1 debloat applied.
The spike app was a throwaway: Kotlin, Compose for TV, an accessibility service and debug buttons. It was installed, measured, and then uninstalled. Its code lives only on the unmerged `spike/home-redirect` branch.

## Answers

| Question | Result | Verdict |
|---|---|---|
| Can pressing Home land on our app? | **Yes.** An accessibility service watches for Amazon's `HomeActivity_vNext` and brings our activity forward. Every press with an app open was redirected across 60 automated presses (Netflix, YouTube, Settings). The owner's physical presses felt "seamless", with no visible flash of Amazon's Home and good speed. | ✅ Pass |
| Does it survive sleep/wake? | **Yes.** The TV was put to sleep and woken, the setting stayed, and the owner confirmed the redirect still worked. | ✅ |
| Does it survive a reboot? | **No.** Fire OS clears `enabled_accessibility_services` at boot. Amazon's accessibility manager (`com.amazon.logan`) only lists allowlisted services, so ours never appears in Settings → Accessibility. It has to be re-enabled from the Mac after a reboot, which is the same moment the owner already flips ADB Debugging. | ⚠️ Workaround |
| Amazon's `HOME_PRESSED` broadcast | Never delivered to a third-party receiver. | ❌ Not usable |
| Resume panel: episode-level data? | **No.** The Watch Next and Preview Programs tables returned 0 rows. Streaming apps don't publish to them on this TV. | App-level only |
| Resume panel: app-level recents? | **Yes.** `UsageStatsManager` works once `appops set <pkg> GET_USAGE_STATS allow` is granted over adb. | ✅ |
| HDMI switching from our app | **Not directly.** The standard passthrough-channel URI is routed into Live TV settings. Amazon switches inputs with `tvinput://tunenow?inputId=…`, which requires `com.amazon.tv.permission.TUNE_INPUT` (protection level `signature\|amazon`). | ❌ Direct, ✅ via Amazon's page |
| Open Amazon's pages from our app | **Yes.** `amzn://com.amazon.tv.launcher/menuNavigation?locationID=<id>` works. | ✅ |
| Compose for TV cost (release build, R8, no baseline profile) | Cold start **0.83 s** (first run 1.12 s), **73 MB** PSS, scroll jank **11%** (90th percentile frame 18 ms). The debug build was much worse (3.5 s). | ✅ start/memory, ⚠️ smoothness |
| On-TV Alexa/AirPlay/updates switches | Not viable. The only route for an app is the TV's own adb service, and network adb turns off on every reboot. | Mac command only |

## Redirect timing (Settings round, 20 presses)

- Press → Amazon Home resumed: about 0.8 s. That's stock Fire TV behavior.
- Amazon Home resumed → our accessibility event: 0.1–0.4 s. → our `startActivity`: about 70 ms. → our activity resumed: a further 0.3–0.5 s.
- Amazon's Home is "resumed" for about 0.5–1.1 s on paper, but it never visibly drew. The owner saw no flash.

## Deep-link location IDs (from the launcher's own logs and strings)

| Our nav item | `locationID` |
|---|---|
| Inputs page | `inputs_destination` |
| Settings | `settings_destination` |
| Home tab | `movies_and_tv_home_tab` |
| Movies | `movies_and_tv_movies_tab` |
| TV Shows | `movies_and_tv_shows_tab` |
| Live | `movies_and_tv_guide_tab` |
| Sports | `movies_and_tv_sports_tab` |
| News | `movies_and_tv_news_tab` |
| Search | `search_tab_v2` |
| Also present | `apps_destination`, `live_destination`, `profile_destination`, `notifications_destination`, `games_destination`, `free_destination`, `ambient_destination` |

These were verified from an adb shell. The real app must re-check them from its own process, since the helper activity resolved as exported. Amazon can rename them in a launcher update, so the app should fail gracefully, for example by opening Amazon's Home.

## Recommendations for Phase 2b

1. **Redirect:** use an accessibility service scoped to `com.amazon.tv.launcher` window-state events. Add `tvclean home on|off` on the Mac to enable or disable it. Have `tvclean status` warn when it's off, which is what a reboot causes.
2. **UI toolkit:** Compose for TV is acceptable on start time and memory, but scrolling must improve before shipping. Add a baseline profile, use a cheaper focus effect (scale plus border, no shadow or elevation animation), and avoid recomposing the hero while it rotates. If jank stays above 5% after that, rebuild the home row in Android Views.
3. **Resume panel:** app-level. Use the 3 most recent apps from the owner's list via UsageStats, with bundled artwork, and "Resume" opens the app. Drop the title/episode/progress line.
4. **Inputs tile:** opens Amazon's Inputs page (`inputs_destination`), one click from there to any HDMI input. Our own overlay can't switch inputs.
5. **Top nav:** deep links per the table above. Settings goes to `settings_destination`.
6. **Alexa/AirPlay/updates switches:** Mac-only (`tvclean feature …`). Don't put them in the on-TV menu.
7. **Memory:** the stock launcher stays resident (it can't be disabled). Our home screen adds roughly 70 MB, which is within the 80 MB budget.
