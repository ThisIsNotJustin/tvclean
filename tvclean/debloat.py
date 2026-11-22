"""Batched debloat: apply catalog entries in reboot-checked batches, reverting a batch on failure."""
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from tvclean.adb import Adb, DeviceUnreachable
from tvclean.apply import Outcome, apply_entry, undo_entry
from tvclean.backup import create_backup
from tvclean.catalog import Entry, select
from tvclean.health import check_health
from tvclean.metrics import collect_metrics
from tvclean.state import read_state

APPLIED_FILE = "applied.json"
UNDONE_STATUSES = ("done", "skipped-already")
APPLIED_STATUSES = ("done", "skipped-already")


@dataclass
class Report:
    backup: Path
    outcomes: list[Outcome]
    reverted: list[str]
    stopped_reason: str | None
    metrics_before: dict
    metrics_after: dict | None


def write_applied(root: Path, data: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / APPLIED_FILE).write_text(json.dumps(data, indent=2) + "\n")


def read_applied(root: Path) -> dict | None:
    path = root / APPLIED_FILE
    if not path.is_file():
        return None
    return json.loads(path.read_text())


def _lost_device_message(backup: Path) -> str:
    return (
        f"Lost contact with the TV during debloat. Backup: {backup}. "
        f"Restore with: tvclean restore {backup.name}"
    )


def _revert(adb: Adb, packages: list[str], backup: Path, reverted: list[str]) -> list[str]:
    """Undo each package, then reboot. Returns detail for any undo that did not succeed."""
    failures: list[str] = []
    for package in packages:
        outcome = undo_entry(adb, package, backup)
        if outcome.status in UNDONE_STATUSES:
            reverted.append(package)
        else:
            failures.append(f"{package}: {outcome.detail or outcome.status}")
    adb.reboot()
    adb.wait_ready()
    return failures


def run_debloat(
    adb: Adb,
    entries: list[Entry],
    *,
    tier: str,
    features_off: set[str],
    root: Path,
    confirm: Callable[[str], bool],
    batch_size: int = 10,
    now: Callable[[], datetime] = datetime.now,
    measure: Callable[[Adb], dict] = collect_metrics,
    log: Callable[[str], None] = print,
) -> Report:
    metrics_before = measure(adb)
    backup = create_backup(adb, root, now(), metrics=metrics_before)
    state = read_state(adb)

    outcomes: list[Outcome] = []
    reverted: list[str] = []
    stopped_reason: str | None = None
    metrics_after: dict | None = None

    todo: list[Entry] = []
    for entry in select(entries, tier, features_off):
        if entry.package not in state.installed:
            outcomes.append(Outcome(entry.package, "skipped-missing"))
        elif entry.action == "disable" and entry.package in state.disabled:
            outcomes.append(Outcome(entry.package, "skipped-already"))
        else:
            todo.append(entry)

    try:
        for number, start in enumerate(range(0, len(todo), batch_size), start=1):
            chunk = todo[start:start + batch_size]
            chunk_outcomes = [apply_entry(adb, entry, state, backup) for entry in chunk]
            outcomes.extend(chunk_outcomes)
            done = [o.package for o in chunk_outcomes if o.status == "done"]
            if not done:
                log(f"Batch {number}: nothing changed")
                continue

            adb.reboot()
            adb.wait_ready()
            problems = check_health(adb)
            if problems:
                failures = _revert(adb, done, backup, reverted)
                stopped_reason = (
                    f"Batch {number} failed health check ({'; '.join(problems)}); batch reverted."
                )
                if failures:
                    stopped_reason += f" Undo incomplete: {'; '.join(failures)}."
                break

            if not confirm(f"Batch {number} done. Remote, picture and an app all OK? [y/N]"):
                failures = _revert(adb, done, backup, reverted)
                stopped_reason = f"Batch {number} not confirmed by owner; batch reverted."
                if failures:
                    stopped_reason += f" Undo incomplete: {'; '.join(failures)}."
                break
            log(f"Batch {number} confirmed")
        else:
            metrics_after = measure(adb)
    except DeviceUnreachable:
        stopped_reason = _lost_device_message(backup)

    applied = sorted({o.package for o in outcomes if o.status in APPLIED_STATUSES} - set(reverted))
    write_applied(root, {
        "tier": tier,
        "features_off": sorted(features_off),
        "packages": applied,
    })

    return Report(
        backup=backup,
        outcomes=outcomes,
        reverted=reverted,
        stopped_reason=stopped_reason,
        metrics_before=metrics_before,
        metrics_after=metrics_after,
    )
