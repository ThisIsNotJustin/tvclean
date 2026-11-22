import json
from dataclasses import dataclass, field
from pathlib import Path

from tvclean.adb import Adb

TRACKED_SETTINGS: tuple[str, ...] = (
    "global:window_animation_scale",
    "global:transition_animation_scale",
    "global:animator_duration_scale",
)


@dataclass(frozen=True)
class DeviceState:
    installed: frozenset[str] = field(default_factory=frozenset)
    disabled: frozenset[str] = field(default_factory=frozenset)
    paths: dict[str, str] = field(default_factory=dict)
    settings: dict[str, str] = field(default_factory=dict)


def _package_lines(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines() if line.strip()]


def _parse_packages(output: str) -> frozenset[str]:
    return frozenset(line.removeprefix("package:") for line in _package_lines(output))


def _parse_paths(output: str) -> dict[str, str]:
    paths: dict[str, str] = {}
    for line in _package_lines(output):
        # Paths can contain "=" (ART directory names such as "~~x==="), so split on the last one.
        rest = line.removeprefix("package:")
        path, _, name = rest.rpartition("=")
        paths[name] = path
    return paths


def read_state(adb: Adb) -> DeviceState:
    installed = _parse_packages(adb.shell("pm list packages"))
    disabled = _parse_packages(adb.shell("pm list packages -d"))
    paths = _parse_paths(adb.shell("pm list packages -f"))
    settings = {}
    for key in TRACKED_SETTINGS:
        namespace, _, name = key.partition(":")
        settings[key] = adb.shell(f"settings get {namespace} {name}").strip()
    return DeviceState(
        installed=installed,
        disabled=disabled,
        paths=paths,
        settings=settings,
    )


def save_state(state: DeviceState, path: Path) -> None:
    data = {
        "installed": sorted(state.installed),
        "disabled": sorted(state.disabled),
        "paths": dict(sorted(state.paths.items())),
        "settings": dict(sorted(state.settings.items())),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def load_state(path: Path) -> DeviceState:
    data = json.loads(path.read_text())
    return DeviceState(
        installed=frozenset(data["installed"]),
        disabled=frozenset(data["disabled"]),
        paths=dict(data["paths"]),
        settings=dict(data["settings"]),
    )
