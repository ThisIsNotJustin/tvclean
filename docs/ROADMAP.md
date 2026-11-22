# tvclean Roadmap

The goal is a fast Insignia Fire TV with an Apple TV-style home screen. Details are in [PLAN.md](PLAN.md), and decisions and progress go in [LEDGER.md](LEDGER.md).

| Phase | What | Branch | Status |
|---|---|---|---|
| 0 | Recon of the TV over ADB, design approved | `main` | ✅ Done |
| 1 | `tvclean` debloat tool: backup, debloat, restore, status, feature toggles (Alexa/AirPlay/updates off by default). Live run on the TV | `phase1-debloat-tool` | ✅ Done (PR) |
| 2a | Throwaway Home-button redirect test. Report only gets merged | `spike/home-redirect` (report only) | ✅ Done |
| 2b | Custom home screen app (mockup B: resume carousel, app row, inputs, Amazon nav tabs, Mac toggles) | `phase2b-home-screen` | ✅ Done (PR) |

## Phase 1: debloat tool
- [x] Project skeleton, adb wrapper, simulated TV for tests
- [x] Protected package list and package catalog loader
- [x] Device state snapshots and backups
- [x] Apply/undo per package (extras are disabled, not uninstalled)
- [x] Memory/launch-time metrics and health checks
- [x] Batched debloat (≤10 per batch, reboot and check, auto-revert)
- [x] Restore, feature toggles, animation and ad-tracking tweaks
- [x] `status` report (drift after Amazon updates) and the CLI
- [x] Curated package list for this TV
- [x] Live run with the owner at the TV: 30 packages disabled, launches ~5–10% faster. The +150 MB free-memory target was **not** met (the biggest users are protected by Fire OS). See [phase1-results.md](phase1-results.md)

## Phase 2a: Home redirect test
- [x] Home lands on our app: every press redirected, no visible flash. Survives sleep/wake. A reboot clears it (re-enable from the Mac)
- [x] Watch Next: not available, so resume is app-level only
- [x] HDMI: no direct switching (Amazon-only permission), opens Amazon's Inputs page instead. Nav tabs: deep links work
- [x] Compose for TV: 0.83 s, 73 MB, but 11% scroll jank (needs work)
- [x] On-TV feature toggles: the Alexa voice switch is on the TV; AirPlay and updates stay on the Mac

Full report: [spike-report.md](spike-report.md)

## Phase 2b: Home screen app
- [x] `home/` app (`dev.tvclean.home`) and `tvclean home install|on|off|status|apps`, a `Home redirect:` status line, and a restart offer after `tvclean feature airplay on`
- [x] Screen: nav pill (☰, Search, Home, Movies, TV Shows, Live, Sports, News), clock, hero "Continue on <App>" carousel over the 3 most recent apps (15 s each, pauses on focus and while the menu is open), app row in the owner's order with an Inputs tile
- [x] Menu: Settings, Inputs, Amazon Home escape (30 s), Alexa voice switch, AirPlay and updates status, About with redirect state
- [x] Artwork is each installed app's own TV banner. Apps that aren't installed are hidden
- [x] Cold start median 634 ms (528–657, 5 runs), budget < 1 s. PSS 75 MB, budget < 80 MB
- [x] Janky frames 0.00% scrolling the app row and during hero rotation (budget ≤ 5%; the 2a spike was 11%)
- [x] Redirect from Netflix: 15/15 presses
- [x] All six nav tabs open the right Amazon tab with no bounce, and Home returns to tvclean Home from each. Settings and Inputs return to Home (Inputs in ~1.7 s)
- [x] Home pressed inside an Amazon tab returns to tvclean Home (focus watching during link sessions)
- [x] Amazon Home escape: Home stays on Amazon for 30 s, then the redirect resumes
- [ ] Owner: real remote presses (Home from inside an Amazon tab, Inputs, Settings)
- [ ] Owner: after the next reboot, check whether the boot self-heal turns the redirect back on (otherwise run `tvclean home on`)
- [ ] Owner: Alexa voice is ON on the TV now. Turn it off from the menu or the Mac
