"""The Home screen app (dev.tvclean.home): install it, turn its accessibility redirect on or off, push the app order."""
import json
import re
from pathlib import Path

from tvclean.adb import Adb
from tvclean.config import REPO_ROOT

HOME_PKG = "dev.tvclean.home"
SERVICE = "dev.tvclean.home/dev.tvclean.home.RedirectService"
DEFAULT_APK = REPO_ROOT / "home/app/build/outputs/apk/release/app-release.apk"
APPS_DIR = "/sdcard/Android/data/dev.tvclean.home/files"
APPS_REMOTE = f"{APPS_DIR}/apps.json"
WRITE_SECURE = "android.permission.WRITE_SECURE_SETTINGS"
ACCESSIBILITY_KEY = "enabled_accessibility_services"
ENABLED_KEY = "accessibility_enabled"
COLOR_PATTERN = re.compile(r"#[0-9A-Fa-f]{6}")


def _services(adb: Adb) -> list[str]:
    raw = adb.shell(f"settings get secure {ACCESSIBILITY_KEY}").strip()
    if raw in ("", "null"):
        return []
    return [part for part in raw.split(":") if part]


def _write_services(adb: Adb, services: list[str], enabled: bool) -> None:
    value = ":".join(services) or '""'
    adb.shell(f"settings put secure {ACCESSIBILITY_KEY} {value}")
    adb.shell(f"settings put secure {ENABLED_KEY} {'1' if enabled else '0'}")


def home_on(adb: Adb) -> None:
    services = _services(adb)
    if SERVICE not in services:
        services.append(SERVICE)
    _write_services(adb, services, enabled=True)


def home_off(adb: Adb) -> None:
    services = [s for s in _services(adb) if s != SERVICE]
    _write_services(adb, services, enabled=bool(services))


def home_install(adb: Adb, apk: Path) -> list[str]:
    adb.install(apk)
    adb.shell(f"pm grant {HOME_PKG} {WRITE_SECURE}")
    adb.shell(f"appops set {HOME_PKG} GET_USAGE_STATS allow")
    adb.shell(f"cmd package compile -m speed -f {HOME_PKG}")
    home_on(adb)
    return [
        f"Installed {HOME_PKG}",
        "Granted WRITE_SECURE_SETTINGS",
        "Allowed usage access",
        "Compiled for speed",
        "Redirect on",
    ]


def home_state(adb: Adb) -> dict:
    listing = adb.shell(f"pm list packages {HOME_PKG}")
    installed = f"package:{HOME_PKG}" in {line.strip() for line in listing.splitlines()}
    state = {
        "installed": installed,
        "version": None,
        "redirect_on": False,
        "secure_settings": False,
        "usage_access": False,
    }
    if not installed:
        return state
    dump = adb.shell(f"dumpsys package {HOME_PKG}")
    version = re.search(r"versionName=(\S+)", dump)
    state["version"] = version.group(1) if version else None
    state["secure_settings"] = f"{WRITE_SECURE}: granted=true" in dump
    state["usage_access"] = "allow" in adb.shell(f"appops get {HOME_PKG} GET_USAGE_STATS")
    state["redirect_on"] = (
        SERVICE in _services(adb)
        and adb.shell(f"settings get secure {ENABLED_KEY}").strip() == "1"
    )
    return state


def _fail(reason: str) -> None:
    raise ValueError(reason)


def validate_apps(text: str) -> None:
    """Raise ValueError with the reason if text is not a valid app order. Mirrors AppCatalog.parse in the app."""
    try:
        root = json.loads(text)
    except json.JSONDecodeError as err:
        _fail(f"invalid catalog JSON: {err}")
    if not isinstance(root, dict):
        _fail("invalid catalog JSON: top level is not an object")
    version = root.get("version")
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        _fail("unsupported catalog version")
    apps = root.get("apps")
    if not isinstance(apps, list):
        _fail("missing apps array")
    if not apps:
        _fail("empty apps array")
    for app in apps:
        if not isinstance(app, dict):
            _fail("invalid catalog JSON: entry is not an object")
        label = app.get("label")
        if not isinstance(label, str) or not label.strip():
            _fail("blank label")
        packages = app.get("packages")
        if not isinstance(packages, list):
            _fail("missing packages")
        if not packages:
            _fail("empty packages")
        for package in packages:
            if not isinstance(package, str) or not package.strip():
                _fail("blank package name")
        color = app.get("color")
        if not isinstance(color, str) or not COLOR_PATTERN.fullmatch(color):
            _fail(f"bad color for {label}")


def push_apps(adb: Adb, path: Path) -> None:
    validate_apps(path.read_text())
    adb.shell(f"mkdir -p {APPS_DIR}")
    adb.push(path, APPS_REMOTE)
