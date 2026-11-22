from tests.fakes import FakeAdb
from tvclean.state import DeviceState, TRACKED_SETTINGS, load_state, read_state, save_state


def test_tracked_settings_are_the_three_animation_keys():
    assert TRACKED_SETTINGS == (
        "global:window_animation_scale",
        "global:transition_animation_scale",
        "global:animator_duration_scale",
    )


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
    assert s.settings == {
        "global:window_animation_scale": "1.0",
        "global:transition_animation_scale": "null",
        "global:animator_duration_scale": "null",
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
