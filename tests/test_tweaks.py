from tests.fakes import FakeAdb
from tvclean.state import TRACKED_SETTINGS
from tvclean.tweaks import TWEAKS, apply_tweaks


def device(**settings) -> FakeAdb:
    return FakeAdb({"com.a": {"enabled": True, "path": "/system/app/a/a.apk"}}, settings=settings)


def test_apply_tweaks_records_old_values():
    f = device(**{"global/window_animation_scale": "1.0", "global/animator_duration_scale": "0.5"})

    changed = apply_tweaks(f)

    assert changed["global:window_animation_scale"] == ("1.0", "0.5")
    assert changed["global:transition_animation_scale"] == ("null", "0.5")
    assert "global:animator_duration_scale" not in changed, "already at target: skipped"
    assert f.settings["global/transition_animation_scale"] == "0.5"


def test_apply_tweaks_second_run_changes_nothing():
    f = device()
    apply_tweaks(f)
    f.calls.clear()

    assert apply_tweaks(f) == {}
    assert not [c for c in f.calls if c.startswith("settings put")]


def test_tweaks_are_tracked_so_restore_can_reset_them():
    assert set(TWEAKS) <= set(TRACKED_SETTINGS)
