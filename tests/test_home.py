from pathlib import Path

import pytest

from tests.fakes import FakeAdb
from tvclean import home
from tvclean.adb import AdbError
from tvclean.config import REPO_ROOT
from tvclean.home import (
    APPS_REMOTE,
    HOME_PKG,
    SERVICE,
    home_install,
    home_off,
    home_on,
    home_state,
    push_apps,
    validate_apps,
)

BUNDLED = REPO_ROOT / "home/app/src/main/assets/apps.json"
ACCESSIBILITY = "secure/enabled_accessibility_services"
ENABLED = "secure/accessibility_enabled"


def home_device(services: str | None = None, enabled: str | None = None, installed: bool = True) -> FakeAdb:
    packages = {"com.safe": {"enabled": True, "path": "/system/app/s/s.apk"}}
    if installed:
        packages[HOME_PKG] = {"enabled": True, "path": "/data/app/home/base.apk"}
    settings = {}
    if services is not None:
        settings[ACCESSIBILITY] = services
    if enabled is not None:
        settings[ENABLED] = enabled
    return FakeAdb(packages, settings=settings)


def test_home_on_appends_and_keeps_others():
    f = home_device(services="a/b.C", enabled="0")

    home_on(f)

    assert f.settings[ACCESSIBILITY] == f"a/b.C:{SERVICE}"
    assert f.settings[ENABLED] == "1"


def test_home_on_from_null():
    f = home_device(services="null")

    home_on(f)

    assert f.settings[ACCESSIBILITY] == SERVICE
    assert f.settings[ENABLED] == "1"


def test_home_on_idempotent():
    f = home_device(services="a/b.C")

    home_on(f)
    home_on(f)

    assert f.settings[ACCESSIBILITY] == f"a/b.C:{SERVICE}"


def test_home_off_removes_only_ours():
    f = home_device(services=f"a/b.C:{SERVICE}", enabled="1")

    home_off(f)

    assert f.settings[ACCESSIBILITY] == "a/b.C"
    assert f.settings[ENABLED] == "1"


def test_home_off_when_ours_alone_empties_list_and_disables():
    f = home_device(services=SERVICE, enabled="1")

    home_off(f)

    assert f.settings[ACCESSIBILITY] == ""
    assert f.settings[ENABLED] == "0"


def test_install_runs_grants_in_order(tmp_path):
    apk = tmp_path / "dev.tvclean.home.apk"
    apk.write_bytes(b"apk")
    f = home_device(installed=False)

    lines = home_install(f, apk)

    assert lines
    cmds = f.calls
    install_at = cmds.index(f"install {apk}")
    grant_at = cmds.index(f"pm grant {HOME_PKG} android.permission.WRITE_SECURE_SETTINGS")
    appops_at = cmds.index(f"appops set {HOME_PKG} GET_USAGE_STATS allow")
    compile_at = cmds.index(f"cmd package compile -m speed -f {HOME_PKG}")
    settings_at = next(i for i, c in enumerate(cmds) if c.startswith("settings put secure enabled_accessibility_services"))
    assert install_at < grant_at < appops_at < compile_at < settings_at
    assert f.grants == {"android.permission.WRITE_SECURE_SETTINGS"}
    assert f.appops[f"{HOME_PKG} GET_USAGE_STATS"] == "allow"
    assert f.settings[ENABLED] == "1"


def test_home_state_reports_all_fields(tmp_path):
    f = home_device(services=SERVICE, enabled="1")
    f.grants.add("android.permission.WRITE_SECURE_SETTINGS")
    f.appops[f"{HOME_PKG} GET_USAGE_STATS"] = "allow"

    state = home_state(f)

    assert state == {
        "installed": True,
        "version": "1.0",
        "redirect_on": True,
        "secure_settings": True,
        "usage_access": True,
    }


def test_home_state_when_not_installed():
    state = home_state(home_device(installed=False))

    assert state["installed"] is False
    assert state["redirect_on"] is False


def test_home_state_redirect_needs_both_list_and_enabled_flag():
    f = home_device(services=SERVICE, enabled="0")

    assert home_state(f)["redirect_on"] is False


@pytest.mark.parametrize("text, reason", [
    ("not json", "invalid catalog JSON"),
    ('["list"]', "invalid catalog JSON"),
    ('{"version": 2, "apps": [{"label": "A", "packages": ["a.b"], "color": "#000000"}]}', "unsupported catalog version"),
    ('{"apps": [{"label": "A", "packages": ["a.b"], "color": "#000000"}]}', "unsupported catalog version"),
    ('{"version": "1", "apps": [{"label": "A", "packages": ["a.b"], "color": "#000000"}]}', "unsupported catalog version"),
    ('{"version": true, "apps": [{"label": "A", "packages": ["a.b"], "color": "#000000"}]}', "unsupported catalog version"),
    ('{"version": 1}', "missing apps array"),
    ('{"version": 1, "apps": {}}', "missing apps array"),
    ('{"version": 1, "apps": []}', "empty apps array"),
    ('{"version": 1, "apps": [{"label": "  ", "packages": ["a.b"], "color": "#000000"}]}', "blank label"),
    ('{"version": 1, "apps": [{"packages": ["a.b"], "color": "#000000"}]}', "blank label"),
    ('{"version": 1, "apps": [{"label": "A", "color": "#000000"}]}', "missing packages"),
    ('{"version": 1, "apps": [{"label": "A", "packages": [], "color": "#000000"}]}', "empty packages"),
    ('{"version": 1, "apps": [{"label": "A", "packages": [""], "color": "#000000"}]}', "blank package name"),
    ('{"version": 1, "apps": [{"label": "A", "packages": [3], "color": "#000000"}]}', "blank package name"),
    ('{"version": 1, "apps": [{"label": "A", "packages": ["a.b"], "color": "000000"}]}', "bad color for A"),
    ('{"version": 1, "apps": [{"label": "A", "packages": ["a.b"], "color": "#00000G"}]}', "bad color for A"),
    ('{"version": 1, "apps": [{"label": "A", "packages": ["a.b"]}]}', "bad color for A"),
    ('{"version": 1, "apps": [3]}', "invalid catalog JSON"),
    ('{"version": 1, "apps": [{"label": "A", "packages": ["a.b", "c.d"], "color": "#000000"}, {"label": "B", "packages": ["c.d"], "color": "#000000"}]}', "package c.d is listed more than once"),
])
def test_validate_apps_rejects(text, reason):
    with pytest.raises(ValueError) as info:
        validate_apps(text)
    assert reason in str(info.value)


def test_validate_apps_accepts_bundled_default():
    validate_apps(BUNDLED.read_text())


def test_push_apps_pushes_to_remote(tmp_path):
    path = tmp_path / "apps.json"
    path.write_text(BUNDLED.read_text())
    f = home_device()

    push_apps(f, path)

    assert f.pushes == [(path, APPS_REMOTE)]
    assert f"mkdir -p {Path(APPS_REMOTE).parent}" in f.calls


def test_push_apps_invalid_pushes_nothing(tmp_path):
    path = tmp_path / "apps.json"
    path.write_text('{"version": 1, "apps": []}')
    f = home_device()

    with pytest.raises(ValueError):
        push_apps(f, path)

    assert f.pushes == []
    assert f.calls == []


def test_constants():
    assert HOME_PKG == "dev.tvclean.home"
    assert SERVICE == "dev.tvclean.home/dev.tvclean.home.RedirectService"
    assert APPS_REMOTE == "/sdcard/Android/data/dev.tvclean.home/files/apps.json"
    assert home.DEFAULT_APK == REPO_ROOT / "home/app/build/outputs/apk/release/app-release.apk"


def test_home_on_raises_when_the_tv_ignores_the_write():
    f = home_device(services="a/b.C", enabled="0")
    f.ignore_settings_writes = {ACCESSIBILITY}

    with pytest.raises(AdbError, match="Could not turn the Home redirect on: the TV did not accept the setting."):
        home_on(f)


def test_home_off_raises_when_the_tv_ignores_the_write():
    f = home_device(services=SERVICE, enabled="1")
    f.ignore_settings_writes = {ACCESSIBILITY}

    with pytest.raises(AdbError, match="Could not turn the Home redirect off"):
        home_off(f)


def test_install_grant_failure_raises_and_names_it(tmp_path):
    apk = tmp_path / "dev.tvclean.home.apk"
    apk.write_bytes(b"apk")
    f = home_device(installed=False)
    f.raw_outputs[f"pm grant {HOME_PKG} android.permission.WRITE_SECURE_SETTINGS"] = "Exception occurred while executing 'grant'\n"

    with pytest.raises(AdbError, match="Could not grant WRITE_SECURE_SETTINGS"):
        home_install(f, apk)


def test_install_appops_failure_raises_and_names_it(tmp_path):
    apk = tmp_path / "dev.tvclean.home.apk"
    apk.write_bytes(b"apk")
    f = home_device(installed=False)
    f.raw_outputs[f"appops set {HOME_PKG} GET_USAGE_STATS allow"] = "Failure calling service appops\n"

    with pytest.raises(AdbError, match="Could not allow usage access"):
        home_install(f, apk)


def test_install_compile_failure_only_warns(tmp_path):
    apk = tmp_path / "dev.tvclean.home.apk"
    apk.write_bytes(b"apk")
    f = home_device(installed=False)
    f.raw_outputs[f"cmd package compile -m speed -f {HOME_PKG}"] = "Error: compile failed\n"

    lines = home_install(f, apk)

    assert any(line.startswith("Warning: compile for speed failed") for line in lines)
    assert lines[-1] == "Redirect on"
    assert f.settings[ENABLED] == "1"


INTENT = "secure/tvclean_home_redirect"


def test_home_off_records_owner_intent_before_removing_service():
    f = home_device(services=SERVICE, enabled="1")
    home_off(f)
    assert f.settings[INTENT] == "0"
    intent_at = f.calls.index("settings put secure tvclean_home_redirect 0")
    service_at = next(i for i, c in enumerate(f.calls) if c.startswith("settings put secure enabled_accessibility_services"))
    assert intent_at < service_at


def test_home_on_records_owner_intent():
    f = home_device(services=None, enabled=None)
    f.settings[INTENT] = "0"
    home_on(f)
    assert f.settings[INTENT] == "1"


def test_install_leaves_intent_on(tmp_path):
    apk = tmp_path / "dev.tvclean.home.apk"
    apk.write_bytes(b"apk")
    f = home_device(installed=False)
    f.settings[INTENT] = "0"
    home_install(f, apk)
    assert f.settings[INTENT] == "1"


def test_home_off_raises_when_intent_write_ignored():
    f = home_device(services=SERVICE, enabled="1")
    f.ignore_settings_writes = {INTENT}
    with pytest.raises(AdbError):
        home_off(f)
    assert SERVICE in f.settings[ACCESSIBILITY]
