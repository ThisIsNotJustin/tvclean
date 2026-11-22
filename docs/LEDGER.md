# tvclean Ledger

A running log of decisions and progress, newest last. Each entry is dated. Decisions record who made them.

## 2026-11-21

**Recon**
- TV: Insignia NS75-UQFL26, Amazon model AFTDEC012E, Fire OS 8.1.8.5 (Android 11). MediaTek MT5896, 4 cores, 32-bit, **1.8 GB RAM with ~680 MB free at idle**. Full notes are in `recon/SUMMARY.md`
- Biggest memory users: Amazon's home screen (~130 MB), then Alexa voice/media services, AirPlay and assorted Amazon background services (~200 MB combined)
- Instagram, The Roku Channel and Pluto TV are preinstalled as ordinary apps
- Amazon's search, input and menu pages can be opened from another app (deep links exist). HDMI 1–4 are standard Android TV inputs

**Decisions**
- SSH isn't used. Everything goes over ADB on Wi-Fi from the Mac (owner)
- FireTV Clean Root rejected: it only supports Fire OS 6/7 (research)
- Approach 1 chosen: debloat tool first, then a custom home screen with a Home-button redirect. Projectivy and "debloat only" rejected (owner)
- Home screen direction: mockup B v2, an Apple TV feel with a 15 s-per-app resume carousel over the last 3 apps, a fixed-order app row, an Inputs tile, and Amazon's top nav kept as quick filters (owner)
- Resume panel is app-level unless the test finds episode data (research: no public API found)
- Alexa, AirPlay and Amazon OTA updates are **off by default**, each with a quick on/off toggle (owner)
- A short flash (≤ ~0.5 s) of Amazon's home before ours is acceptable (owner)
- Never disable or uninstall Amazon's launcher. System packages are only disabled per user, never uninstalled (design)
- Preinstalled extras: save the APK into the backup before removing them, so `restore` can reinstall (design)
- Debloat tool: Python 3, stdlib only, tested against a simulated TV (design)
- Workflow: one branch and pull request per change, reviewed and merged by the owner. Planning docs stay local, and the repo keeps PLAN, ROADMAP and LEDGER (owner)

**Progress**
- `main`: plan, recon summary, mockup
- Next: Phase 1 on `phase1-debloat-tool`

## 2026-11-21 (Phase 1 build and live run)

**Decisions made during the build** (owner decisions marked; the rest were build calls)
- adb errors: a lost TV is reported separately from a failed command. Every change is re-checked against the TV's real state instead of trusting command output
- The record of what tvclean changed is cumulative across runs, so `status` can spot anything an Amazon update re-enables
- `tvclean restore` only moves the TV back toward stock, never disables anything. With no name it goes back to the **first** backup (the TV before tvclean); `restore <name>` rolls back to a specific point
- Two Amazon-private settings whose meaning was only guessed from their names are left out of the tweaks. `debloat --no-tweaks` skips the tweaks entirely
- AirPlay's real package is `com.apple.airplay.amazon.airplay`. `com.amazon.airplaydaemon` is only its process name
- The post-batch check covers Home, Settings, HDMI switching, search and opening an app. Each run reboots once for a clean baseline before measuring
- After each reboot, tvclean pauses and asks the owner to flip ADB Debugging off and on (owner chose this over a permanent adb setting)
- Preinstalled extras (Instagram, Roku Channel, Pluto TV) are disabled, never uninstalled
- The catalog keeps only packages that actually work on this TV (owner ran the "what sticks" test)
- tvclean no longer changes `animator_duration_scale`. It breaks the Home menu's Settings and Inputs

**Live findings**
- Network adb turns off on every reboot (the switch still shows On). Flipping it restores it
- Fire OS refuses to disable 9 catalog packages (protected), including the main update services, tcomm and device messaging. `vizzini` (Alexa voice) turns itself back on at every boot
- 30 packages disabled and stable. Launches ~5–10% faster. Free memory unchanged (613 vs 625–665 MB), so the +150 MB target was not met
- The menu breakage was the animator tweak, not any package. It was found by reverting settings one at a time and confirmed across a reboot
- The owner uninstalled Instagram by hand

**Progress**
- Phase 1 complete: `phase1-debloat-tool` opened as a PR. Results are in `docs/phase1-results.md`
- Next: Phase 2a, the Home-button redirect test

## 2026-11-22 (Phase 2a spike)

**Findings** (details in `docs/spike-report.md`)
- The Home redirect via an accessibility service works: seamless, no visible flash, good speed (owner). It survives sleep/wake. Fire OS clears it on every reboot (Amazon's accessibility manager allowlists services)
- No episode-level resume data (Watch Next is empty). App-level recents work
- Third-party apps can't switch HDMI (Amazon-signature permission). Amazon's Inputs page and its top-nav tabs open via `amzn://com.amazon.tv.launcher/menuNavigation?locationID=…`
- Compose for TV, release build: 0.83 s cold start, 73 MB, 11% scroll jank (over budget)

**Decisions**
- Phase 2b proceeds with the accessibility-service redirect, plus `tvclean home on|off` from the Mac after reboots (build call; the redirect met the owner's flash tolerance)
- The resume panel is app-level. The Inputs tile opens Amazon's Inputs page. Alexa/AirPlay/updates switches stay Mac-only (build calls forced by platform limits)

## 2026-11-22 (Phase 2b home screen)

**Decisions** (owner decisions are marked; the rest were build calls)
- AirPlay is **off by default** after the live test (owner). Turning it off stops it at once; turning it back on needs a restart. Apps can't enable or disable packages, so AirPlay stays a Mac command
- Build autonomously overnight, one branch and pull request (owner)
- Link sessions: every Amazon page lands on Amazon's Home, so the redirect ignores Home for 2.5 s after the app opens a page, restarted when the tab link is actually sent. Amazon's tab links only work when Amazon's Home is on screen, so the app opens Amazon's Home first and sends the tab link ~0.8 s later
- Focus watching: during a link session the redirect watches which nav tab has focus (a bounded walk of the accessibility tree, since the plain focus lookup returns no id) and returns when Amazon's Home tab gets focus. Pressing Home inside an Amazon tab fires no window event. After Home on the Inputs page Amazon is silent for ~10 s, so the redirect also checks once a second for up to 2 minutes of a session
- Banner artwork: each installed app's own TV banner. YouTube TV, HBO Max and Apple TV aren't installed on this TV, so they're hidden until installed
- The hero shows "CONTINUE ON <APP>" with one "▶ Resume" button ("▶ Open" when there is nothing to resume)
- Compile for speed instead of a baseline profile: `cmd package compile -m speed` runs at install, since Fire OS can't generate profiles without root
- The menu panel is opaque. The carousel pauses on focus and while the menu is open

**Live findings**
- Cold start median 634 ms (528–657, 5 runs). PSS 75 MB. Janky frames 0.00% scrolling the app row (371 frames) and during hero rotation (140 frames)
- Redirect from Netflix: 15/15 presses. All six nav tabs open the right Amazon tab with no bounce, and Home returns to tvclean Home from each. Settings returns to Home. Inputs returns to Home in ~1.7 s
- Amazon Home escape: Home stays on Amazon for 30 s, then the redirect resumes
- AirPlay on uses ~224 MB. Turning it off freed ~112 MB of available memory
- The accessibility service can't capture remote key events on Fire OS
- Alexa voice is ON on this TV (`voice_disabled=0`). The menu's switch or the Mac can turn it off

**Progress**
- Phase 2b built on `phase2b-home-screen`: the home app, the `tvclean home` commands, the status line, and the AirPlay restart offer
- Next: owner checks with a real remote and a reboot (see the Phase 2b checklist in [ROADMAP.md](ROADMAP.md))
