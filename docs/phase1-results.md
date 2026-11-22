# Phase 1 results: debloat on the real TV

Date: 2026-11-21. TV: Insignia NS75-UQFL26, Fire OS 8.1.8.5 (RS8185/3898).

## Outcome

- **30 packages disabled, and they stay disabled across reboots.** They cover ads, sponsored content, recommendations, telemetry and logging, Alexa's media and notification services, AirPlay, Amazon's forced-update helper, tutorials, Roku Channel and Pluto TV. Instagram was uninstalled by hand from the TV.
- **Privacy and animation tweaks are applied:** window and transition animation scales at 0.5, ad tracking limited (3 settings), and usage-metrics upload off.
- **Everything checked still works:** remote, picture, Home, the hamburger menu's Settings and Inputs, typed search, HDMI switching, Netflix, YouTube and Disney+.
- The owner reports the TV feels noticeably smoother.

## Measurements

Each measurement was taken after a clean reboot. Cold launch is the time to the app's first screen (`am start -W`).

| | Stock (run 1) | Stock (run 2) | Debloated |
|---|---|---|---|
| Netflix | 1950 ms | 2157 ms | 1852 ms |
| YouTube | 1447 ms | 1510 ms | 1377 ms |
| Disney+ | 2156 ms | 2173 ms | 2087 ms |
| MemAvailable | 665 MB | 625 MB | 613 MB |

- App launches are about 5–10% faster.
- **Free memory did not improve.** The spec's +150 MB target was not met. The biggest memory users can't be disabled on this firmware: the stock launcher (~130 MB), Settings, the Alexa voice service (`vizzini`), `tcomm` and device messaging. Fire OS either refuses to disable them or turns them back on.

## What the real TV taught us

1. **Network adb turns off on every reboot.** The Developer Options switch still shows On, but port 5555 stays closed until it's flipped off and on. tvclean now pauses after each reboot and asks the owner to flip it.
2. **Fire OS protects many packages.** `pm disable-user` is refused for: ftvads.deeplinking, device.crashmanager, device.logmanager, device.metrics, device.messaging, tcomm, tv.csapp, device.software.ota and device.software.ota.override. So Amazon updates can only be partly blocked.
3. **`com.amazon.vizzini` (Alexa voice) is re-enabled at every boot.**
4. **Setting `animator_duration_scale` to 0.5 breaks the hamburger menu's Settings and Inputs.** It caused all three times the menu "broke": both batch failures and once after the final run. It was found by reverting settings one group at a time with no reboot, and then confirmed across a reboot. The package bisect had cleared every package, which pointed at the tweaks. tvclean no longer changes this setting. Window and transition animation scales at 0.5 are safe and stay on.
5. **Uninstalling the extras was replaced by disabling them.** Same memory benefit, fully reversible, and nothing on the TV is uninstalled by tvclean.
6. **Package state reads were confusing during the hunt.** Several packages seemed to come back on after a reboot when they were disabled one at a time. In the final all-at-once test, all 30 stayed off through 6 minutes of uptime. Only `vizzini` reliably comes back. tvclean's `status` reports any drift.

## Undo

`tvclean restore` goes back to the first backup (`20261121-205812`, the TV before tvclean). It reinstalls Instagram from the APK saved during the first run.

## Follow-ups

- When the updates feature can't disable the main OTA packages, `status` should not say "Amazon updates are OFF".
- After each reboot, tvclean should check that the packages it applied are still disabled and report any that Fire OS turned back on.
- `reboot()` should only swallow `error: closed` and timeouts.
- Phase 2: the custom home screen. The stock launcher stays resident, because it can't be disabled.
