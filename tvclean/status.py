"""Status report: what is off, what Amazon re-enabled since the last run, and the TV's memory."""
from dataclasses import dataclass, field
from pathlib import Path

from tvclean.adb import Adb, DeviceUnreachable
from tvclean.catalog import FEATURES, Entry
from tvclean.debloat import read_applied
from tvclean.metrics import mem_available_kb
from tvclean.state import list_disabled, list_installed


@dataclass
class StatusReport:
    connected: bool
    firmware: str = ""
    disabled: list[str] = field(default_factory=list)
    drift: list[str] = field(default_factory=list)
    features: dict[str, bool] = field(default_factory=dict)
    mem_available_kb: int = 0


def _firmware(adb: Adb) -> str:
    return adb.shell("getprop ro.build.version.name").strip()


def build_status(adb: Adb, entries: list[Entry], root: Path) -> StatusReport:
    try:
        installed = list_installed(adb)
        disabled = list_disabled(adb)
        firmware = _firmware(adb)
        mem_kb = mem_available_kb(adb)
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
    )


def format_status(r: StatusReport) -> str:
    lines: list[str] = []
    if not r.features.get("updates", True):
        lines.append("⚠ Amazon updates are OFF — run 'tvclean feature updates on' to update.")
    lines.append(f"Firmware: {r.firmware}")
    lines.append(f"MemAvailable: {r.mem_available_kb // 1024} MB")
    for name in FEATURES:
        state = "on" if r.features.get(name) else "off"
        lines.append(f"Feature {name}: {state}")
    lines.append(f"Disabled packages: {len(r.disabled)}")
    if r.drift:
        lines.append(
            f"Re-enabled since last run (likely an Amazon update): {', '.join(r.drift)}. "
            "Run 'tvclean debloat' again."
        )
    return "\n".join(lines)
