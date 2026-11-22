# tvclean

Debloats a Fire TV over adb. It turns off Amazon and vendor apps it doesn't need, saves a backup first, and can put everything back.

## Install

Needs Python 3.13 and adb (Android platform-tools). Nothing needs installing beyond that: `bin/tvclean` runs from the repo and uses `.venv` if one exists. To install the `tvclean` command instead, run `pip install -e .`.

Enable ADB debugging on the TV (Settings → My Fire TV → Developer options → ADB debugging). tvclean connects to the TV itself on each run, so no separate `adb connect` is needed.

The defaults are device `192.168.1.253:5555` and adb at `~/Library/Android/sdk/platform-tools/adb`. Override them with `--device` / `TVCLEAN_DEVICE` and `TVCLEAN_ADB`.

## Running

From the repo, run `bin/tvclean <command>`. Its examples below use `tvclean`, which is the same command.

## Commands

```
tvclean status                    # features, disabled packages, memory, Amazon re-enables
tvclean debloat                   # turn off the bloat (batches of 10, reboot and check after each)
tvclean debloat --tier moderate   # also turn off the moderate-tier extras
tvclean debloat --keep alexa      # leave Alexa on (also: airplay, updates)
tvclean debloat --yes             # confirm each batch without asking
tvclean debloat --no-tweaks       # leave the animation and ad-tracking settings alone
tvclean feature airplay off       # turn a feature off; use 'on' to turn it back on
tvclean backup                    # save the TV's current state now
tvclean backups                   # list backups
tvclean restore                   # restore to your first backup (see below)
tvclean restore 20261121-101500   # roll back to a specific backup
```

Each run that changes the TV takes a backup first, in `backups/`.

Debloat starts by showing its plan, for example `120 packages in 12 batches → 12 reboots (about 60 minutes)`, and asks `Start? [y/N]`. `--yes` skips that question and the per-batch ones. The run first reboots the TV once so the baseline is measured on a freshly started TV. Then each batch goes like this: disable the packages, reboot, wait 45 seconds, run the health checks (retried up to three times), and ask you to check the TV. The check covers the remote, the picture, Home and Settings, switching to an HDMI input and back, search from Home, and opening one app. Answer `y` if all of that works. If not, that batch is undone.

After each reboot the TV may stop accepting adb until you turn ADB debugging off and on again. When that happens tvclean tells you what to do: on the TV, go to Settings → My Fire TV → Developer options and switch ADB debugging off, then on. Then press Enter in the terminal to carry on, or type `q` to stop. This also happens with `--yes`.

Progress is printed as each phase starts. When a run ends, it prints any package that was refused or failed, the packages that were undone, and the memory and Netflix/YouTube/Disney+ launch times before and after. Each backup also gets a `report.json` with the outcome of every package and the same numbers.

Pressing Ctrl-C stops the run. It prints the backup name, and `tvclean restore` undoes the run.

`debloat`, `feature` and `restore` first check that the connected device is the TV this tool was built for (`ro.product.device` is `ginza`). If it isn't, they stop with `Connected device is <x>, not this TV (ginza). Check --device.` and change nothing.

## Feature toggles

`tvclean feature <name> on|off` switches a group of packages. Each run takes a backup first.

- `updates off` on this TV only blocks Amazon's forced-update helper (`com.amazon.tv.forcedotaupdater.v2`). The main update services are protected by Fire OS and can't be disabled, so updates may still arrive. Run `tvclean status` after any update.
- `alexa off` turns off Alexa's media and notification services. But Fire OS keeps the core voice service running.

## Undo

`tvclean restore` with no name restores to your first backup, which is the TV as it was before tvclean. Pass a backup NAME to roll back to that point instead.

Restore re-enables disabled apps and reinstalls removed ones. It also resets the tweaked settings.

## Updating the TV

Amazon updates can turn disabled apps back on. Run this routine after an update:

1. `tvclean feature updates on`
2. Let the TV update.
3. `tvclean debloat`
4. `tvclean status`

`status` warns when updates are off, and lists any packages that came back since the last run. It also lists the disabled packages by name. After a debloat run it shows free memory and Netflix's cold-launch time, compared with the first backup.

## If something goes wrong

If a command says some items could not be restored or switched, run it again. Each run only changes what is still wrong, so a second run is safe.

If the TV drops off during a run, the message gives the backup name. Once the TV is back on the network, run `tvclean restore` to return it to stock.

If the TV is in a bad state and restore doesn't fix it, reset it: Settings → My Fire TV → Reset to Factory Defaults. This erases everything, so set the TV up again afterwards.

## What it changes

tvclean never uninstalls anything on the TV. It turns apps off for your user only, with `pm disable-user`. That includes Instagram, Roku Channel and Pluto TV. They are disabled rather than uninstalled, because Roku Channel and Pluto TV register TV inputs that Amazon's Home navigation menu relies on.

Backups stay in `backups/` on your machine and are gitignored.
