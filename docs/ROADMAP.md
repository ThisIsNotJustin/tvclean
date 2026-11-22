# tvclean Roadmap

The goal is a fast Insignia Fire TV with an Apple TV-style home screen. Details are in [PLAN.md](PLAN.md), and decisions and progress go in [LEDGER.md](LEDGER.md).

| Phase | What | Branch | Status |
|---|---|---|---|
| 0 | Recon of the TV over ADB, design approved | `main` | ✅ Done |
| 1 | `tvclean` debloat tool: backup, debloat, restore, status, feature toggles (Alexa/AirPlay/updates off by default). Live run on the TV | `phase1-debloat-tool` | ⏳ Next |
| 2a | Throwaway Home-button redirect test. Report only gets merged | `spike/home-redirect` | Planned |
| 2b | Custom home screen app (mockup B: resume carousel, app row, inputs, Amazon nav tabs, on-TV toggles) | TBD | Planned after 2a's report |

## Phase 1: debloat tool
- [ ] Project skeleton, adb wrapper, simulated TV for tests
- [ ] Protected package list and package catalog loader
- [ ] Device state snapshots and backups
- [ ] Apply/undo per package (save the APK before removing extras)
- [ ] Memory/launch-time metrics and health checks
- [ ] Batched debloat (≤10 per batch, reboot and check, auto-revert)
- [ ] Restore, feature toggles, animation and ad-tracking tweaks
- [ ] `status` report (drift after Amazon updates) and the CLI
- [ ] Curated package list for this TV
- [ ] Live run with the owner at the TV. Target: +150 MB free memory

## Phase 2a: Home redirect test
- [ ] Home lands on our app with ≤ ~0.5 s flash, 60/60 presses
- [ ] Watch Next (episode-level resume) available?
- [ ] HDMI switching and nav-tab deep links from our app
- [ ] Compose-for-TV cost: < 1 s cold start, < 80 MB, smooth scrolling
- [ ] On-TV feature toggles feasible?

## Phase 2b: Home screen app
To be planned from the 2a report.
