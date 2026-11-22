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
