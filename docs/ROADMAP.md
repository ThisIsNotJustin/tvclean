# tvclean Roadmap

The goal is a fast Insignia Fire TV with an Apple TV-style home screen. Details are in [PLAN.md](PLAN.md), and decisions and progress go in [LEDGER.md](LEDGER.md).

| Phase | What | Branch | Status |
|---|---|---|---|
| 0 | Recon of the TV over ADB, design approved | `main` | ✅ Done |
| 1 | `tvclean` debloat tool: backup, debloat, restore, status, feature toggles (Alexa/AirPlay/updates off by default). Live run on the TV | `phase1-debloat-tool` | ✅ Done (PR) |
| 2a | Throwaway Home-button redirect test. Report only gets merged | `spike/home-redirect` (report only) | ✅ Done |
| 2b | Custom home screen app (mockup B: resume carousel, app row, inputs, Amazon nav tabs, on-TV toggles) | TBD | ⏳ Next |

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
- [x] On-TV feature toggles: not viable, Mac command only

Full report: [spike-report.md](spike-report.md)

## Phase 2b: Home screen app
To be planned from the 2a report.
