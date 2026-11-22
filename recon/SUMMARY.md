# TV recon summary (read-only, 2026-11-21)

Raw dumps live alongside this file. Nothing on the TV was changed.

## Device
- Amazon model AFTDEC012E, codename `ginza`. Insignia NS75-UQFL26
- Fire OS 8.1.8.5 (RS8185/3898N), Android 11 / SDK 30
- SoC MediaTek MT5896 (`merak`), 4 cores, Mali GPU, **32-bit userspace (armeabi-v7a)**
- **RAM 1.8 GB total, ~680 MB available** at idle on the home screen. `ro.lmk.low_perf_device=true`
- UI renders at 1920x1080 (density 320), and the panel is 3840x2160
- Storage: 8.9 GB, 6.6 GB free

## Memory hogs (PSS, idle on home)
| Process | MB |
|---|---|
| com.amazon.tv.launcher (stock home) | 130 |
| com.amazon.tv.settings.v2 | 126 |
| com.amazon.vizzini (Alexa voice) | 49 |
| com.amazon.device.services | 33 |
| com.amazon.tcomm | 27 |
| com.amazon.aria | 21 |
| Alexa media players (2) | 31 |
| airplaydaemon | 14 |
| whisperjoin (2) | 20 |
| neo.minerva | 12 |

## Packages
- 257 system, 11 third-party, 0 disabled
- Third-party apps: YouTube (com.amazon.firetv.youtube), Hulu, Paramount+ (com.cbs.ott), Netflix, Disney+, **plus preinstalled extras: Instagram (com.instagram.airwave), The Roku Channel (com.roku.web.trc), Pluto TV**
- OTA: com.amazon.device.software.ota, .ota.override, com.amazon.tv.forcedotaupdater.v2

## Home / launcher
- Default HOME is `com.amazon.tv.launcher/.ui.HomeActivity_vNext` (priv-app in /system_ext, updated in /data, v7321874.1)
- Launcher exposes `com.amazon.tv.launcher.HOME_PRESSED` and a protected HOME_LONGPRESSED permission
- No accessibility services enabled

## Deep links into Amazon screens (exist and are exported; not yet test-launched)
- Search: `com.amazon.intent.action.SHOW_TEXT_SEARCH`, `amzn://…/search`
- Nav menu pages: `amzn://…/navmenu`, `/menuNavigation` (NavMenuScreenDeepLinkActivityDI). Likely how Movies, TV Shows, Live, Sports and News are reached; node IDs still unknown
- Inputs: `com.amazon.tv.action.NAVIGATE_TO_INPUTS`
- Recents: `com.amazon.tv.action.NAVIGATE_TO_RECENTS`; the launcher also has an `AppRecencyReceiver`

## HDMI
- Standard Android TV inputs: `com.mediatek.tis/.HdmiInputService/HW2..HW5` (HW3, HW4 and HW5 report state 1; the TV's current state needs checking)
- A third-party app can switch inputs with the standard passthrough-channel intent (`TvContract.buildChannelUriForPassthroughInput`). Needs a live test

## Resume data
- `com.android.providers.tv` (TvProvider) is present, so Watch Next may be readable; whether apps publish to it is untested
- App-level recency is available via UsageStats (grantable over adb appops)
