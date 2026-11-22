import pytest
from datetime import datetime

from tests.fakes import FakeAdb
from tvclean.adb import AdbError
from tvclean.backup import create_backup, list_backups
from tvclean.state import DeviceState, TRACKED_SETTINGS, load_state, read_state, save_state


def test_tracked_settings_are_the_animation_and_ad_usage_keys():
    assert TRACKED_SETTINGS[:3] == (
        "global:window_animation_scale",
        "global:transition_animation_scale",
        "global:animator_duration_scale",
    )
    assert "secure:limit_ad_tracking" in TRACKED_SETTINGS


def test_read_state_parses_paths_with_equals_in_dir():
    f = FakeAdb({"com.a": {"enabled": False, "path": "/data/app/~~x==/com.a-y==/base.apk"}})
    s = read_state(f)
    assert s.paths["com.a"] == "/data/app/~~x==/com.a-y==/base.apk"
    assert "com.a" in s.disabled
    assert "com.a" in s.installed


def test_read_state_reads_tracked_settings_and_keeps_null():
    f = FakeAdb(
        {"com.a": {"enabled": True, "path": "/system/app/a/a.apk"}},
        settings={"global/window_animation_scale": "1.0"},
    )
    s = read_state(f)
    assert s.settings == {key: "null" for key in TRACKED_SETTINGS} | {
        "global:window_animation_scale": "1.0",
    }


def test_read_state_only_lists_enabled_packages_as_not_disabled():
    f = FakeAdb(
        {
            "com.on": {"enabled": True, "path": "/system/app/on/on.apk"},
            "com.off": {"enabled": False, "path": "/system/app/off/off.apk"},
        }
    )
    s = read_state(f)
    assert s.disabled == frozenset({"com.off"})
    assert s.installed == frozenset({"com.on", "com.off"})


def test_state_roundtrip(tmp_path):
    f = FakeAdb(
        {"com.a": {"enabled": False, "path": "/data/app/~~x==/com.a-y==/base.apk"}},
        settings={"global/window_animation_scale": "0.5"},
    )
    s = read_state(f)
    save_state(s, tmp_path / "s.json")
    assert load_state(tmp_path / "s.json") == s


def test_saved_state_has_sorted_lists(tmp_path):
    import json

    s = DeviceState(
        installed=frozenset({"b", "a"}),
        disabled=frozenset({"d", "c"}),
        paths={"a": "/x"},
        settings={},
    )
    save_state(s, tmp_path / "s.json")
    data = json.loads((tmp_path / "s.json").read_text())
    assert data["installed"] == ["a", "b"]
    assert data["disabled"] == ["c", "d"]


def test_read_state_ignores_non_package_lines():
    f = FakeAdb(
        {"com.a": {"enabled": True, "path": "/system/app/a/a.apk"}},
        raw_outputs={
            "pm list packages": "Error: Could not access the Package Manager\npackage:com.a\n",
            "pm list packages -d": "",
            "pm list packages -f": "cmd: noise\npackage:/system/app/a/a.apk=com.a\n",
        },
    )
    s = read_state(f)
    assert s.installed == frozenset({"com.a"})
    assert s.paths == {"com.a": "/system/app/a/a.apk"}


def test_read_state_raises_on_empty_package_list(tmp_path):
    f = FakeAdb(
        {"com.a": {"enabled": True, "path": "/system/app/a/a.apk"}},
        raw_outputs={"pm list packages": "cmd: Can't find service: package\n"},
    )
    with pytest.raises(AdbError, match="Can't find service"):
        read_state(f)
    with pytest.raises(AdbError):
        create_backup(f, tmp_path, datetime(2026, 11, 21, 18, 5, 9))
    assert list_backups(tmp_path) == []


def test_read_state_skips_path_line_without_equals():
    f = FakeAdb(
        {"com.b": {"enabled": True, "path": "/x/b.apk"}},
        raw_outputs={"pm list packages -f": "package:/system/app/a.apk\npackage:/x/b.apk=com.b\n"},
    )
    s = read_state(f)
    assert s.paths == {"com.b": "/x/b.apk"}


@pytest.mark.parametrize(
    "output",
    [
        "Exception occurred while executing 'get'",
        "error: no such namespace",
        "line one\nline two",
    ],
)
def test_read_state_raises_on_settings_error_output(output):
    f = FakeAdb(
        {"com.a": {"enabled": True, "path": "/system/app/a/a.apk"}},
        raw_outputs={"settings get global window_animation_scale": output},
    )
    with pytest.raises(AdbError, match="global:window_animation_scale"):
        read_state(f)
