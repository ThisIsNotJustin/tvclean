"""Feature toggles: switch an optional feature's packages off (disable) or back on (undo)."""
from datetime import datetime
from pathlib import Path
from typing import Callable

from tvclean.adb import Adb
from tvclean.apply import Outcome, apply_entry, undo_entry
from tvclean.backup import create_backup, latest_backup
from tvclean.catalog import FEATURES, Entry
from tvclean.debloat import read_applied, write_applied
from tvclean.restore import find_apk_dir
from tvclean.state import read_state

__all__ = ["FEATURES", "set_feature"]
DONE_STATUSES = ("done", "skipped-already")


def set_feature(
    adb: Adb,
    entries: list[Entry],
    name: str,
    on: bool,
    root: Path,
    now: Callable[[], datetime] = datetime.now,
) -> list[Outcome]:
    if name not in FEATURES:
        raise ValueError(f"unknown feature {name!r}; expected one of {', '.join(FEATURES)}")
    feature_entries = [e for e in entries if e.feature == name]
    applied = read_applied(root) or {"tier": None, "features_off": [], "packages": []}

    if not on:
        backup = create_backup(adb, root, now())
        state = read_state(adb)
        outcomes = [apply_entry(adb, e, state, backup) for e in feature_entries]
        applied["packages"] = sorted(
            set(applied["packages"]) | {o.package for o in outcomes if o.status in DONE_STATUSES}
        )
        applied["features_off"] = sorted(set(applied["features_off"]) | {name})
    else:
        fallback = latest_backup(root) or root
        outcomes = [
            undo_entry(adb, e.package, find_apk_dir(root, e.package, fallback))
            for e in feature_entries
        ]
        restored = {o.package for o in outcomes if o.status in DONE_STATUSES}
        applied["packages"] = sorted(set(applied["packages"]) - restored)
        if all(o.status in DONE_STATUSES for o in outcomes):
            applied["features_off"] = sorted(set(applied["features_off"]) - {name})

    write_applied(root, applied)
    return outcomes
