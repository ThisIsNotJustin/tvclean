# tvclean

Debloats a Fire TV over adb. It turns off Amazon and vendor apps it doesn't need, saves a backup first, and can put everything back.

## Install

Needs Python 3.13 and adb (Android platform-tools). Nothing needs installing beyond that: `bin/tvclean` runs from the repo and uses `.venv` if one exists. To install the `tvclean` command instead, run `pip install -e .`.

Enable ADB debugging on the TV (Settings → My Fire TV → Developer options → ADB debugging), then connect:

```
adb connect 192.168.1.253:5555
```

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

Each run that changes the TV takes a backup first, in `backups/`. Debloat asks you to confirm after each batch: check that the remote, the picture and an app still work, then answer `y`. If not, that batch is undone.

## Undo

`tvclean restore` with no name restores to your first backup, which is the TV as it was before tvclean. Pass a backup NAME to roll back to that point instead.

Restore re-enables disabled apps and reinstalls removed ones. It also resets the tweaked settings.

## Updating the TV

Amazon updates can turn disabled apps back on. Run this routine after an update:

1. `tvclean feature updates on`
2. Let the TV update.
3. `tvclean debloat`
4. `tvclean status`

`status` warns when updates are off, and lists any packages that came back since the last run.

## Last resort: factory reset

If the TV is in a bad state and restore doesn't fix it, reset it: Settings → My Fire TV → Reset to Factory Defaults. This erases everything, so set the TV up again afterwards.

## What it changes

tvclean never uninstalls Amazon or vendor system apps. It turns them off for your user only, with `pm disable-user`. The only apps it uninstalls are Instagram, Roku Channel and Pluto TV, which are preinstalled third-party apps. Each APK is copied into the backup first, so restore can reinstall it.

Backups stay in `backups/` on your machine and are gitignored.
