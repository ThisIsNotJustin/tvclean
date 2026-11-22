"""Apply one catalog entry to the TV, and undo it from a backup."""
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tvclean.adb import Adb, AdbError, DeviceUnreachable
from tvclean.catalog import Entry
from tvclean.state import DeviceState, list_disabled, list_installed

DATA_APP_PREFIX = "/data/app/"
REFUSAL_PATTERN = re.compile(r"Exception|not allowed|Cannot disable")

Status = Literal["done", "skipped-missing", "skipped-already", "refused", "failed"]


@dataclass(frozen=True)
class Outcome:
    package: str
    status: Status
    detail: str = ""


def _apply_disable(adb: Adb, package: str, state: DeviceState) -> Outcome:
    if package in state.disabled:
        return Outcome(package, "skipped-already")
    output = adb.shell(f"pm disable-user --user 0 {package}")
    if REFUSAL_PATTERN.search(output) or package not in list_disabled(adb):
        return Outcome(package, "refused", output.strip())
    return Outcome(package, "done")


def _apk_paths(output: str) -> list[str]:
    """Each `package:` line of `pm path` output is one APK of the package."""
    return [line for line in output.splitlines() if line.strip().startswith("package:")]


def _apply_uninstall(adb: Adb, package: str, state: DeviceState, backup_dir: Path) -> Outcome:
    path = state.paths.get(package, "")
    if not path.startswith(DATA_APP_PREFIX):
        return Outcome(package, "refused", "system package; use disable")
    if len(_apk_paths(adb.shell(f"pm path {shlex.quote(package)}"))) > 1:
        # Only base.apk is pulled, so a split install could not be restored from the backup.
        return Outcome(package, "refused", "split APK; not uninstalled")
    apk = backup_dir / "apks" / f"{package}.apk"
    apk.parent.mkdir(parents=True, exist_ok=True)
    try:
        adb.pull(path, apk)
    except DeviceUnreachable:
        raise  # device lost: the batch runner must see it, not a per-package failure
    except AdbError as err:
        return Outcome(package, "failed", str(err))
    if not apk.is_file() or apk.stat().st_size == 0:
        return Outcome(package, "failed", "pulled APK missing or empty; not uninstalled")
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
    if package not in list_installed(adb):
        if apk.is_file():
            try:
                adb.install(apk)
            except DeviceUnreachable:
                raise  # device lost: the batch runner must see it, not a per-package failure
            except AdbError as err:
                return Outcome(package, "failed", str(err))
            if package not in list_installed(adb):
                return Outcome(package, "failed", f"pm list packages does not show {package} after install")
            return Outcome(package, "done")
        output = adb.shell(f"cmd package install-existing {package}")
        if package not in list_installed(adb):
            return Outcome(package, "failed", output.strip())
        return Outcome(package, "done")
    if package in list_disabled(adb):
        output = adb.shell(f"pm enable {package}")
        if package in list_disabled(adb):
            return Outcome(package, "failed", output.strip())
        return Outcome(package, "done")
    return Outcome(package, "skipped-already")
