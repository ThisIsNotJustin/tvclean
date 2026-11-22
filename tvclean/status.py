"""Status report: what is off, what Amazon re-enabled since the last run, and the TV's memory."""
import json
from dataclasses import dataclass, field
from pathlib import Path

from tvclean.adb import Adb, DeviceUnreachable
from tvclean.backup import list_backups
from tvclean.catalog import FEATURES, Entry
from tvclean.debloat import REPORT_FILE, read_applied
from tvclean.home import home_state
from tvclean.metrics import mem_available_kb
from tvclean.state import list_disabled, list_installed

NETFLIX = "com.netflix.ninja"


@dataclass
class StatusReport:
    connected: bool
    firmware: str = ""
    disabled: list[str] = field(default_factory=list)
    drift: list[str] = field(default_factory=list)
    features: dict[str, bool] = field(default_factory=dict)
    mem_available_kb: int = 0
    # The first backup's metrics, and the metrics_after of the latest run's report.json.
    baseline: dict | None = None
    latest: dict | None = None
    # home_state of the Home screen app; None when the app is not installed.
    home: dict | None = None


def _read_json(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.is_file() else None


def _first_metrics(root: Path) -> dict | None:
    for backup in list_backups(root):
        metrics = _read_json(backup / "metrics.json")
        if metrics is not None:
            return metrics
    return None


def _latest_metrics(root: Path) -> dict | None:
    for backup in reversed(list_backups(root)):
        report = _read_json(backup / REPORT_FILE)
        if report is not None:
            return report.get("metrics_after")
    return None


def _firmware(adb: Adb) -> str:
    return adb.shell("getprop ro.build.version.name").strip()


def build_status(adb: Adb, entries: list[Entry], root: Path) -> StatusReport:
    try:
        installed = list_installed(adb)
        disabled = list_disabled(adb)
        firmware = _firmware(adb)
        mem_kb = mem_available_kb(adb)
        home = home_state(adb)
    except DeviceUnreachable:
        return StatusReport(connected=False)

    def enabled_or_installed(package: str) -> bool:
        return package in installed and package not in disabled

    applied = read_applied(root) or {"packages": []}
    drift = sorted(p for p in applied["packages"] if enabled_or_installed(p))
    features = {
        name: any(enabled_or_installed(e.package) for e in entries if e.feature == name)
        for name in FEATURES
    }
    return StatusReport(
        connected=True,
        firmware=firmware,
        disabled=sorted(disabled),
        drift=drift,
        features=features,
        mem_available_kb=mem_kb,
        baseline=_first_metrics(root),
        latest=_latest_metrics(root),
        home=home if home["installed"] else None,
    )


def _comparison_lines(baseline: dict, latest: dict) -> list[str]:
    lines: list[str] = []
    if latest.get("mem_available_kb") is not None:
        before_kb = baseline["mem_available_kb"] // 1024
        after_kb = latest["mem_available_kb"] // 1024
        lines.append(f"Free memory: {before_kb} MB → {after_kb} MB ({after_kb - before_kb:+d})")
    before_ms = baseline.get("cold_launch_ms", {}).get(NETFLIX)
    after_ms = latest.get("cold_launch_ms", {}).get(NETFLIX)
    if before_ms is not None and after_ms is not None:
        lines.append(f"Netflix cold launch: {before_ms} ms → {after_ms} ms")
    return lines


def format_status(r: StatusReport) -> str:
    lines: list[str] = []
    if not r.features.get("updates", True):
        lines.append("⚠ Amazon updates are OFF — run 'tvclean feature updates on' to update.")
    lines.append(f"Firmware: {r.firmware}")
    lines.append(f"MemAvailable: {r.mem_available_kb // 1024} MB")
    for name in FEATURES:
        state = "on" if r.features.get(name) else "off"
        lines.append(f"Feature {name}: {state}")
    if r.home is not None:
        lines.append(
            "Home redirect: on" if r.home["redirect_on"] else "Home redirect: OFF (run: tvclean home on)"
        )
    lines.append(f"Disabled packages: {len(r.disabled)}")
    lines.extend(f"  {package}" for package in r.disabled)
    if r.baseline and r.latest:
        lines.extend(_comparison_lines(r.baseline, r.latest))
    if r.drift:
        lines.append(
            f"Re-enabled since last run (likely an Amazon update): {', '.join(r.drift)}. "
            "Run 'tvclean debloat' again."
        )
    return "\n".join(lines)
