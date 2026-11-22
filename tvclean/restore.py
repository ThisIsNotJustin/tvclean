"""Restore the TV to a backup: re-enable, reinstall and reset tracked settings."""
import shlex
from pathlib import Path

from tvclean.adb import Adb
from tvclean.apply import Outcome, undo_entry
from tvclean.backup import list_backups
from tvclean.debloat import read_applied, write_applied
from tvclean.state import (
    TRACKED_SETTINGS,
    DeviceState,
    list_disabled,
    list_installed,
    load_state,
    read_state,
    setting_reads_back,
)

UNDONE_STATUSES = ("done", "skipped-already")


class NoBackups(Exception):
    """There is no backup to restore from."""


def find_apk_dir(root: Path, package: str, fallback: Path) -> Path:
    """Newest backup holding an APK for `package`, else `fallback` (undo then installs existing)."""
    for backup in reversed(list_backups(root)):
        if (backup / "apks" / f"{package}.apk").is_file():
            return backup
    return fallback


def _restore_setting(adb: Adb, key: str, current: str, target: str) -> Outcome:
    namespace, _, name = key.partition(":")
    if target == "null":
        adb.shell(f"settings delete {shlex.quote(namespace)} {shlex.quote(name)}")
    else:
        adb.shell(f"settings put {shlex.quote(namespace)} {shlex.quote(name)} {shlex.quote(target)}")
    if not setting_reads_back(adb, key, target):
        return Outcome(key, "failed", f"{current} -> {target} did not read back")
    return Outcome(key, "done", f"{current} -> {target}")


def run_restore(adb: Adb, root: Path, name: str | None = None) -> list[Outcome]:
    """Restore to backup `name`, or to the oldest backup (the pre-tvclean snapshot) when no name is given."""
    backups = list_backups(root)
    if not backups:
        raise NoBackups("no backups found in backups/")
    if name is None:
        target_dir = backups[0]
    else:
        target_dir = root / name
        if not target_dir.is_dir():
            raise FileNotFoundError(f"no backup named {name} in backups/")

    target = load_state(target_dir / "state.json")
    now: DeviceState = read_state(adb)
    outcomes: list[Outcome] = []

    for package in sorted(target.installed - now.installed):
        apk_dir = find_apk_dir(root, package, target_dir)
        outcomes.append(undo_entry(adb, package, apk_dir))

    for package in sorted(target.installed & (now.disabled - target.disabled)):
        apk_dir = find_apk_dir(root, package, target_dir)
        outcomes.append(undo_entry(adb, package, apk_dir))

    restored = {o.package for o in outcomes if o.status in UNDONE_STATUSES}

    for key in TRACKED_SETTINGS:
        wanted = target.settings.get(key)
        if wanted is None:
            continue  # older backups may predate this key
        current = now.settings.get(key)
        if current != wanted:
            outcomes.append(_restore_setting(adb, key, current, wanted))

    applied = read_applied(root) or {"tier": None, "features_off": [], "packages": []}
    remaining = set(applied["packages"]) - restored
    if name is None:
        # Restoring to stock: a recorded package that is installed and enabled is already at stock.
        installed_now = list_installed(adb)
        disabled_now = list_disabled(adb)
        remaining = {p for p in remaining if not (p in installed_now and p not in disabled_now)}
    applied["packages"] = sorted(remaining)
    if not applied["packages"]:
        applied["features_off"] = []
        applied["tier"] = None
    write_applied(root, applied)
    return outcomes
