# tvclean Plan

Date: 2026-11-21
Status: approved by owner 2026-11-21

## 1. Intent

The owner's 75" Insignia Fire TV has slowed down until it's nearly unusable. Pressing Home lands on a screen crowded with sponsored rows, "you may like" sections and recommended apps. The owner wants:

1. **A fast TV again**, by removing or disabling what the hardware can't afford.
2. **A home screen they actually want**, with the polish of Apple TV's software: a large "resume" area for recent apps, their streaming apps, input switching, and Amazon's top nav (which they use as quick filters). No sponsored or recommendation content on Home.

## 2. The device (measured 2026-11-21, see `recon/SUMMARY.md`)

- Insignia NS75-UQFL26, Amazon model AFTDEC012E (`ginza`), Fire OS 8.1.8.5 (Android 11 / SDK 30)
- MediaTek MT5896, 4 cores, Mali GPU, **32-bit userspace (armeabi-v7a)**
- **1.8 GB RAM, ~680 MB available at idle**. The system flags itself `low_perf_device`
- UI at 1920x1080 (density 320) on a 4K panel
- Stock launcher `com.amazon.tv.launcher` uses ~130 MB. Alexa voice/media, AirPlay, whisperjoin, aria, tcomm and similar services use ~200 MB more
- Preinstalled extras installed as ordinary apps: Instagram (`com.instagram.airwave`), The Roku Channel (`com.roku.web.trc`), Pluto TV (`tv.pluto.android`)
- Connection: ADB over Wi-Fi at 192.168.1.253:5555, already authorized for the owner's Mac. adb lives at `~/Library/Android/sdk/platform-tools/adb`

## 3. Goals, non-goals, anti-goals

**Goals**
- Measurably more free memory and faster app launches after Phase 1
- Home button leads to the custom home screen (Phase 2)
- Custom home matches mockup B v2 (`docs/mockups/home-b-v2.html`). The mockup sets the look (proportions, hierarchy, style). Section 6.3 sets behavior. Where they differ, 6.3 wins. Exact sizes and spacing are the builder's, judged on the real TV
- Every change is reversible from the Mac with one command

**Non-goals**
- Rooting, kernel exploits, or flashing firmware (FireTV Clean Root is out: Fire OS 6/7 only)
- Rebuilding Amazon's Movies, TV Shows, Live, Sports or News pages. Those tabs open Amazon's own pages
- Title-level "resume" (episode and progress) as a requirement. Only app-level is guaranteed (see 6.3)
- Supporting other TVs or Fire TV sticks

**Anti-goals (failure even if it "works")**
- The custom home screen is itself sluggish, or janky when moving between tiles
- Anything that bricks the TV, causes a boot loop, or breaks Settings, the remote, HDMI-CEC, input switching, Wi-Fi or picture settings
- A setup the owner can't undo without help
- Sponsored or recommended content anywhere on the custom Home

## 4. Approaches considered

| | Approach | Trade-off | Verdict |
|---|---|---|---|
| 1 | **Debloat script now, then a custom home screen app** with a Home-button redirect helper | Most work. Home redirect may flash the stock screen briefly and can be broken by Amazon updates | **Chosen by owner** |
| 2 | Debloat, then Projectivy launcher themed to match | Far less to build, but no 15-second resume carousel, no Amazon-style nav, not the owner's design | Rejected |
| 3 | Debloat only, keep Amazon's home | Sponsored rows come from Amazon's servers and can't be removed | Rejected (its debloat part is Phase 1) |

## 5. Phase 1: debloat tool

A command-line tool run on the owner's Mac (zsh/bash, needs only adb). Commands:

- `backup`: snapshot the package state (enabled/disabled/installed lists, relevant `settings` values) into a timestamped folder under `backups/`. Runs automatically before any change
- `debloat [--tier safe|moderate]`: apply the package list for that tier
- `restore [backup]`: return to a snapshot (re-enable everything disabled, `cmd package install-existing` anything removed for user 0)
- `status`: show what's currently disabled and the memory and launch-time numbers

**Package list** lives in a data file (not hard-coded), one entry per package with a tier, the action (`disable-user` / `uninstall-user0`) and a one-line reason. Rules:
- Preinstalled extras (Instagram, Roku Channel, Pluto TV) are removed for user 0
- Every Amazon/MediaTek system package uses `pm disable-user --user 0`, never full uninstall
- **Protected list** (never touched): anything for Settings, input/HDMI/CEC (`com.mediatek.tis`, `com.amazon.tv.devicecontrol`, `com.amazon.tv.inputpreference.service`), picture quality (`com.mediatek.customerpq`), remote/Bluetooth pairing, IME, system UI, the stock launcher itself, Wi-Fi/network, package installer, and Live TV/tuner services
- Candidates come from community lists (Fire-Tools Debloat.txt, FireFrame debloat.txt, CleanYourTV, dumbtv), cross-checked against this TV's actual package list (`recon/packages_all.txt`)
- **Apply in batches and verify after each:** reboot, then check that Home, Settings, the remote, input switching, Wi-Fi and one streaming app all work. Revert the batch on failure

**Extras (safe tier):** cut animation scales to 0.5, and turn off ad-tracking / interest-based ads and usage-data collection where adb can reach them.

**Evidence:** record `MemAvailable` and cold-launch time (`am start -W`) for Netflix, YouTube and Disney+ before and after, and keep them in `backups/<timestamp>/metrics.txt`.

**Success threshold (builder's call, marked as such):** target at least +150 MB `MemAvailable` at idle and noticeably faster cold launches. Stop adding to the `moderate` tier once a batch gives no measurable gain, or at the first breakage. OTA, Alexa and AirPlay are separate feature toggles, not part of any tier. Per section 9, `debloat` turns all three off by default.

**Recovery (builder's call):**
- Wi-Fi, networking, Settings and remote pairing are on the protected list, so adb stays reachable
- Every disable is user-0 only, so a factory reset (Settings → My Fire TV → Reset) always returns stock. That's the last resort, and the owner should know it exists
- Batches are small (≤10 packages), with a reboot and check after each

## 6. Phase 2: custom home screen

### 6.1 Spike first (throwaway)

A bare-bones APK to answer the riskiest question: **can we make Home land on our app on Fire OS 8.1.8.5?** It tests, in order:
1. An accessibility service that sees `com.amazon.tv.launcher/.ui.HomeActivity_vNext` come to the foreground and immediately starts our activity. Measure the visible flash
2. Whether the `com.amazon.tv.launcher.HOME_PRESSED` broadcast reaches a third-party receiver
3. Read-only: whether TvProvider's Watch Next table returns rows from Netflix, Disney+, Hulu and the others (feeds 6.3)
4. Memory and cold-start of an empty Compose-for-TV screen on this 32-bit device

Spike output is a short written report. If Home redirect isn't workable, stop and return to the owner before building 6.2.

**What the spike may change (builder's call):** it may test `cmd package set-home-activity` and similar, but only changes that can be undone over adb, with a backup taken first. It must never disable or uninstall the stock launcher or its receivers.

**Escape hatches (required in 6.2):** the custom home has a visible "Amazon Home" entry in the menu that opens the stock launcher. The accessibility service can be turned off from the remote (Settings → Accessibility) and with `tvclean home off` from the Mac.

### 6.2 The app

- **Stack:** Kotlin, Jetpack Compose for TV (`androidx.tv`), minSdk 30, armeabi-v7a. Fall back to Android Views if the spike shows Compose is over budget
- **Performance budget:** cold start under 1 s; under 80 MB PSS; focus movement at 60 fps with no dropped frames during the hero rotation. Measured on this TV, not an emulator
- **Install:** `adb install` from the Mac. Usage-stats access granted via `adb shell appops set <pkg> GET_USAGE_STATS allow`. The accessibility service is enabled via `settings put secure enabled_accessibility_services`
- **The stock launcher stays installed and enabled** (disabling it risks breaking Fire OS). It may stay resident in memory. Reducing that is the builder's to investigate, never by disabling it

### 6.3 Screen design (mockup B v2)

- **Top nav** (pill, centered): menu, Search, **Home** (selected), Movies, TV Shows, Live, Sports, News. Search uses `com.amazon.intent.action.SHOW_TEXT_SEARCH`. The other tabs deep-link into Amazon's pages (`amzn://…/navmenu` / NavMenuScreenDeepLinkActivityDI). Exact targets are found by watching logcat while tapping each tab on the stock home. Menu opens Fire TV Settings
- **Clock** top right
- **Hero "resume" carousel**, about 60% of the screen height: the 3 most recently used apps from the owner's app list (UsageStats), most recent first. **15 s per slide**, then back to slide 1. Progress dots show the timer. Rotation pauses while the hero has focus. Each slide shows big app-branded artwork, "Continue on <App>", and buttons **Resume** (launch the app) and **Open <App>**. If the spike finds Watch Next data for that app, show the title, episode and progress bar. Otherwise those lines are omitted
- **App row**, labeled "Your apps", **fixed order**: Disney+, Hulu, Prime Video, Paramount+, Netflix, YouTube, YouTube TV, HBO Max, Apple TV, then an **Inputs** tile. Apps not yet installed are hidden, not greyed out. Order lives in a config file editable from the Mac
- **Inputs tile** opens a small overlay listing HDMI 1–4 (`com.mediatek.tis/.HdmiInputService/HW2..HW5`), switched via the passthrough-channel intent. Fallback: `com.amazon.tv.action.NAVIGATE_TO_INPUTS`
- **Look:** dark, Apple TV-like. Large artwork, SF-like system sans, translucent nav pill, the focused tile scales ~1.1x with a soft shadow and white outline. No heavy real-time blur. Artwork is bundled with the app (no network fetches)
- **No** sponsored, recommended or "you may like" content anywhere

## 7. Constraints

- No root. Everything over ADB from the owner's Mac or inside normal app permissions
- 32-bit, 1.8 GB RAM device. Every feature must respect the 6.2 budget
- Amazon OTA updates may re-enable packages or break the Home redirect. The tool's `status` command must detect both
- The owner's serial number, MAC and SSID stay out of git and out of any external request

## 8. Build workflow

- **Opus** (main session): orchestrator and final reviewer. Owns the plan, signs off each phase, talks to the owner
- **Sonnet** agents: manage and review the Haiku agents for a task, then report to Opus
- **Haiku** agents: research, explore and write code
- Every on-TV change goes through the backup/verify/revert loop in section 5. Agents never run destructive adb commands without a backup taken first

## 9. Owner decisions

- [x] **Alexa voice and AirPlay: off by default, with a quick way to turn each back on** (owner, 2026-11-21). Two named toggles, `alexa` and `airplay`, each mapping to its group of packages:
  - From the Mac: `tvclean feature alexa on|off`, `tvclean feature airplay on|off`
  - On the TV: an "Alexa" and an "AirPlay" switch in the custom home screen's menu. An ordinary app can't re-enable packages itself, so the builder decides how (for example the app talking to the TV's own adb service on localhost after a one-time "allow" prompt, as on-device adb tools do). If no on-TV route works, the Mac command plus a note on Fire TV Settings → Applications is the fallback, and the builder reports that to the owner
- [x] **Amazon OTA updates: off by default, with a toggle** (owner, 2026-11-21). Same pattern as Alexa/AirPlay: a third feature, `updates`, controlled by `tvclean feature updates on|off` and an "Updates" switch in the custom menu. Covers `com.amazon.device.software.ota`, `.ota.override` and `com.amazon.tv.forcedotaupdater.v2` (builder confirms that's the full set). `status` shows prominently that updates are off. The suggested routine is: switch updates on, let the TV update, then re-run `debloat` and `status`, since an update may re-enable packages or break the Home redirect
- [x] **Home flash: a short flash is fine** (owner, 2026-11-21). Up to about 0.5 s of Amazon's home before ours appears passes the spike. Longer than that, or an unreliable redirect, means stop and return to the owner

## 10. Left to the builder

- Exact package list per tier, within the protected-list rules
- Script language details, file layout, the config format
- How the accessibility service is scoped (minimum event types and packages)
- Artwork production for each app's hero slide and tile
- Exact deep-link targets for each nav tab
- Package IDs for apps not yet installed (Prime Video is built in; YouTube TV, HBO Max and Apple TV get resolved once installed). Missing apps stay hidden
- Toolchain: install a JDK and Android SDK build-tools via the Android CLI already on the Mac. Debug-signed APK, `applicationId` of the builder's choosing. `adb install` doesn't need "unknown sources"
