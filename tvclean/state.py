import json
from dataclasses import dataclass, field
from pathlib import Path

from tvclean.adb import Adb, AdbError

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


PACKAGE_PREFIX = "package:"
ERROR_SNIPPET_CHARS = 200


def _package_lines(output: str) -> list[str]:
    """Lines of `pm list packages` output. Only `package:` lines are data; anything else is noise."""
    return [
        line.strip()[len(PACKAGE_PREFIX):]
        for line in output.splitlines()
        if line.strip().startswith(PACKAGE_PREFIX)
    ]


def _parse_packages(output: str) -> frozenset[str]:
    return frozenset(_package_lines(output))


def _parse_paths(output: str) -> dict[str, str]:
    paths: dict[str, str] = {}
    for rest in _package_lines(output):
        # Paths can contain "=" (ART directory names such as "~~x==="), so split on the last one.
        if "=" not in rest:
            continue
        path, _, name = rest.rpartition("=")
        paths[name] = path
    return paths


def list_installed(adb: Adb) -> frozenset[str]:
    """Packages `pm list packages` reports on the TV right now."""
    return _parse_packages(adb.shell("pm list packages"))


def list_disabled(adb: Adb) -> frozenset[str]:
    """Packages `pm list packages -d` reports as disabled right now."""
    return _parse_packages(adb.shell("pm list packages -d"))


def _read_setting(adb: Adb, key: str) -> str:
    namespace, _, name = key.partition(":")
    value = adb.shell(f"settings get {namespace} {name}").strip()
    if "\n" in value or value.lower().startswith(("error", "exception")):
        raise AdbError(f"settings get failed for {key}: {value[:ERROR_SNIPPET_CHARS]}")
    return value


def read_state(adb: Adb) -> DeviceState:
    installed_output = adb.shell("pm list packages")
    installed = _parse_packages(installed_output)
    if not installed:
        raise AdbError(
            "pm list packages returned no packages: "
            f"{installed_output[:ERROR_SNIPPET_CHARS]}"
        )
    disabled = list_disabled(adb)
    paths = _parse_paths(adb.shell("pm list packages -f"))
    settings = {key: _read_setting(adb, key) for key in TRACKED_SETTINGS}
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
