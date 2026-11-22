"""Apply one catalog entry to the TV, and undo it from a backup."""
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tvclean.adb import Adb, AdbError, DeviceUnreachable
from tvclean.catalog import Entry
from tvclean.state import DeviceState, _parse_packages

DATA_APP_PREFIX = "/data/app/"
REFUSAL_PATTERN = re.compile(r"Exception|not allowed|Cannot disable")

Status = Literal["done", "skipped-missing", "skipped-already", "refused", "failed"]


@dataclass(frozen=True)
class Outcome:
    package: str
    status: Status
    detail: str = ""


def _disabled_now(adb: Adb) -> frozenset[str]:
    return _parse_packages(adb.shell("pm list packages -d"))


def _installed_now(adb: Adb) -> frozenset[str]:
    return _parse_packages(adb.shell("pm list packages"))


def _apply_disable(adb: Adb, package: str, state: DeviceState) -> Outcome:
    if package in state.disabled:
        return Outcome(package, "skipped-already")
    output = adb.shell(f"pm disable-user --user 0 {package}")
    if REFUSAL_PATTERN.search(output) or package not in _disabled_now(adb):
        return Outcome(package, "refused", output.strip())
    return Outcome(package, "done")


def _apply_uninstall(adb: Adb, package: str, state: DeviceState, backup_dir: Path) -> Outcome:
    path = state.paths.get(package, "")
    if not path.startswith(DATA_APP_PREFIX):
        return Outcome(package, "refused", "system package; use disable")
    apk = backup_dir / "apks" / f"{package}.apk"
    apk.parent.mkdir(parents=True, exist_ok=True)
    try:
        adb.pull(path, apk)
    except DeviceUnreachable:
        raise
    except AdbError as err:
        return Outcome(package, "failed", str(err))
    output = adb.shell(f"pm uninstall --user 0 {package}")
    if "Success" not in output:
        return Outcome(package, "failed", output.strip())
    return Outcome(package, "done")


def apply_entry(adb: Adb, entry: Entry, state: DeviceState, backup_dir: Path) -> Outcome:
    package = entry.package
    if package not in state.installed:
        return Outcome(package, "skipped-missing")
    if entry.action == "disable":
        return _apply_disable(adb, package, state)
    return _apply_uninstall(adb, package, state, backup_dir)


def undo_entry(adb: Adb, package: str, backup_dir: Path) -> Outcome:
    apk = backup_dir / "apks" / f"{package}.apk"
    installed = package in _installed_now(adb)
    if not installed:
        if apk.is_file():
            adb.install(apk)
            return Outcome(package, "done")
        adb.shell(f"cmd package install-existing {package}")
        if package not in _installed_now(adb):
            return Outcome(package, "failed", "install-existing did not restore the package")
        return Outcome(package, "done")
    if package in _disabled_now(adb):
        adb.shell(f"pm enable {package}")
        return Outcome(package, "done")
    return Outcome(package, "skipped-already")
