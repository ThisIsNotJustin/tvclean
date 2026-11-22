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
