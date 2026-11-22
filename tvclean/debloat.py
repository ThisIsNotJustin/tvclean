"""Batched debloat: apply catalog entries in reboot-checked batches, reverting a batch on failure."""
import json
import math
import time
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
from tvclean.tweaks import apply_tweaks

APPLIED_FILE = "applied.json"
REPORT_FILE = "report.json"
UNDONE_STATUSES = ("done", "skipped-already")
APPLIED_STATUSES = ("done", "skipped-already")
# Seconds after a reboot before health checks: Home and the HDMI inputs settle slowly.
SETTLE_S = 45
HEALTH_ATTEMPTS = 3
HEALTH_RETRY_S = 30
MINUTES_PER_BATCH = 5
RECONNECT_PROMPT = (
    "The TV isn't accepting adb after the reboot (this TV turns network adb off on every restart). "
    "When the TV's Home screen is back: Settings → My Fire TV → Developer Options → turn ADB Debugging OFF, then ON. "
    "Then press Enter here (or type q to stop)."
)
RECONNECT_PROMPTS = 3
CONFIRM_PROMPT = (
    "Batch {n} done. Check: remote works, picture OK, Home and Settings open, "
    "switch to an HDMI input and back, search from Home, open one app. All OK? [y/N]"
)


def plan_line(count: int, batch_size: int = 10) -> str:
    """The up-front plan: how many packages, in how many batches, and so how many reboots."""
    batches = math.ceil(count / batch_size)
    return (
        f"{count} packages in {batches} batches → {batches} reboots "
        f"(about {batches * MINUTES_PER_BATCH} minutes)"
    )


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
        "Restore with: tvclean restore"
    )


def _write_report(
    backup: Path,
    outcomes: list[Outcome],
    reverted: list[str],
    stopped_reason: str | None,
    metrics_before: dict,
    metrics_after: dict | None,
) -> None:
    """Save what the run did next to the backup, so the owner can read it after the fact."""
    data = {
        "outcomes": [{"package": o.package, "status": o.status, "detail": o.detail} for o in outcomes],
        "reverted": reverted,
        "stopped_reason": stopped_reason,
        "metrics_before": metrics_before,
        "metrics_after": metrics_after,
    }
    (backup / REPORT_FILE).write_text(json.dumps(data, indent=2) + "\n")


def _wait_for_tv(
    adb: Adb,
    reconnect: Callable[[str], bool] | None,
    wait_timeout_s: int,
) -> None:
    """Wait for adb after a reboot. If the TV stays off adb, ask the owner to toggle it and retry."""
    try:
        adb.wait_ready(timeout_s=wait_timeout_s)
        return
    except DeviceUnreachable as err:
        if reconnect is None:
            raise
        last = err
    for _ in range(RECONNECT_PROMPTS):
        if not reconnect(RECONNECT_PROMPT):
            raise last
        try:
            adb.wait_ready(timeout_s=wait_timeout_s)
            return
        except DeviceUnreachable as err:
            last = err
    raise last


def _revert(
    adb: Adb,
    packages: list[str],
    backup: Path,
    reverted: list[str],
    *,
    settle_s: float,
    sleep: Callable[[float], None],
    log: Callable[[str], None],
    reconnect: Callable[[str], bool] | None,
    wait_timeout_s: int,
) -> list[str]:
    """Undo each package, then reboot. Returns detail for any undo that did not succeed."""
    failures: list[str] = []
    for package in packages:
        outcome = undo_entry(adb, package, backup)
        if outcome.status in UNDONE_STATUSES:
            reverted.append(package)
        else:
            failures.append(f"{package}: {outcome.detail or outcome.status}")
    log("Rebooting (up to 4 min)…")
    adb.reboot()
    _wait_for_tv(adb, reconnect, wait_timeout_s)
    log("Waiting for the TV to settle…")
    sleep(settle_s)
    return failures


def _health_with_retries(
    adb: Adb, *, retry_s: float, sleep: Callable[[float], None], log: Callable[[str], None]
) -> list[str]:
    """Problems after the settle time. Only a failure on every attempt counts as a problem."""
    problems: list[str] = []
    for attempt in range(1, HEALTH_ATTEMPTS + 1):
        log("Running health checks…")
        problems = check_health(adb)
        if not problems:
            return []
        if attempt < HEALTH_ATTEMPTS:
            log(f"Health check failed ({'; '.join(problems)}); retrying in {retry_s:g} s…")
            sleep(retry_s)
    return problems


def _record_applied(
    root: Path, tier: str, features_off: set[str], outcomes: list[Outcome], reverted: list[str]
) -> None:
    """Write applied.json cumulatively: earlier runs' packages stay until reverted."""
    previous = read_applied(root)
    carried = set(previous["packages"]) if previous else set()
    this_run = {o.package for o in outcomes if o.status in APPLIED_STATUSES}
    write_applied(root, {
        "tier": tier,
        "features_off": sorted(features_off),
        "packages": sorted((carried | this_run) - set(reverted)),
    })


def run_debloat(
    adb: Adb,
    entries: list[Entry],
    *,
    tier: str,
    features_off: set[str],
    root: Path,
    confirm: Callable[[str], bool],
    batch_size: int = 10,
    tweaks: bool = True,
    now: Callable[[], datetime] = datetime.now,
    measure: Callable[[Adb], dict] = collect_metrics,
    log: Callable[[str], None] = print,
    baseline_reboot: bool = True,
    settle_s: float | None = None,
    health_retry_s: float | None = None,
    sleep: Callable[[float], None] = time.sleep,
    reconnect: Callable[[str], bool] | None = None,
    wait_timeout_s: int = 150,
) -> Report:
    settle = SETTLE_S if settle_s is None else settle_s
    retry = HEALTH_RETRY_S if health_retry_s is None else health_retry_s
    if baseline_reboot:
        # Nothing has changed yet, so the baseline is measured on a freshly booted TV.
        log("Rebooting for a clean baseline…")
        adb.reboot()
        _wait_for_tv(adb, reconnect, wait_timeout_s)
    log("Measuring baseline (the TV will open Netflix, YouTube and Disney+ by itself)…")
    metrics_before = measure(adb)
    backup = create_backup(adb, root, now(), metrics=metrics_before)

    outcomes: list[Outcome] = []
    reverted: list[str] = []
    stopped_reason: str | None = None
    metrics_after: dict | None = None

    try:
        state = read_state(adb)
        todo: list[Entry] = []
        for entry in select(entries, tier, features_off):
            if entry.package not in state.installed:
                outcomes.append(Outcome(entry.package, "skipped-missing"))
            elif entry.action == "disable" and entry.package in state.disabled:
                outcomes.append(Outcome(entry.package, "skipped-already"))
            else:
                todo.append(entry)
        batches = [todo[i:i + batch_size] for i in range(0, len(todo), batch_size)]
        log(f"Plan: {plan_line(len(todo), batch_size)}")

        changed, failed_tweaks = apply_tweaks(adb) if tweaks else ({}, [])
        for key, (old, new_value) in changed.items():
            log(f"Tweak {key}: {old} -> {new_value}")
        for key in failed_tweaks:
            log(f"Tweak {key} did not read back as set; left as is")

        for number, chunk in enumerate(batches, start=1):
            log(f"Batch {number}/{len(batches)}: disabling {', '.join(e.package for e in chunk)}…")
            chunk_outcomes: list[Outcome] = []
            for entry in chunk:
                try:
                    outcome = apply_entry(adb, entry, state, backup)
                except DeviceUnreachable:
                    # The change may have landed before the TV dropped; record it so the report names it.
                    outcomes.append(Outcome(entry.package, "failed", "device lost mid-apply; state unknown"))
                    raise
                outcomes.append(outcome)
                chunk_outcomes.append(outcome)
            done = [o.package for o in chunk_outcomes if o.status == "done"]
            if not done:
                log(f"Batch {number}: nothing changed")
                continue

            log("Rebooting (up to 4 min)…")
            adb.reboot()
            _wait_for_tv(adb, reconnect, wait_timeout_s)
            log("Waiting for the TV to settle…")
            sleep(settle)
            problems = _health_with_retries(adb, retry_s=retry, sleep=sleep, log=log)
            if problems:
                failures = _revert(
                    adb, done, backup, reverted, settle_s=settle, sleep=sleep, log=log,
                    reconnect=reconnect, wait_timeout_s=wait_timeout_s,
                )
                stopped_reason = (
                    f"Batch {number} failed health check ({'; '.join(problems)}); batch reverted."
                )
                if failures:
                    stopped_reason += f" Undo incomplete: {'; '.join(failures)}."
                break

            if not confirm(CONFIRM_PROMPT.format(n=number)):
                failures = _revert(
                    adb, done, backup, reverted, settle_s=settle, sleep=sleep, log=log,
                    reconnect=reconnect, wait_timeout_s=wait_timeout_s,
                )
                stopped_reason = f"Batch {number} not confirmed by owner; batch reverted."
                if failures:
                    stopped_reason += f" Undo incomplete: {'; '.join(failures)}."
                break
            log(f"Batch {number} confirmed")
        else:
            log("Measuring results…")
            metrics_after = measure(adb)
    except DeviceUnreachable:
        stopped_reason = _lost_device_message(backup)
    except BaseException:
        stopped_reason = f"Stopped unexpectedly. Packages may be disabled. Backup: {backup.name}."
        log(f"{stopped_reason} Restore with: tvclean restore")
        raise
    finally:
        _record_applied(root, tier, features_off, outcomes, reverted)
        _write_report(backup, outcomes, reverted, stopped_reason, metrics_before, metrics_after)

    return Report(
        backup=backup,
        outcomes=outcomes,
        reverted=reverted,
        stopped_reason=stopped_reason,
        metrics_before=metrics_before,
        metrics_after=metrics_after,
    )
