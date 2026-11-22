from tests.fakes import FakeAdb
from tvclean.state import TRACKED_SETTINGS
from tvclean.tweaks import TWEAKS, apply_tweaks


def device(**settings) -> FakeAdb:
    return FakeAdb({"com.a": {"enabled": True, "path": "/system/app/a/a.apk"}}, settings=settings)


def test_apply_tweaks_records_old_values():
    f = device(**{"global/window_animation_scale": "1.0", "global/animator_duration_scale": "0.5"})

    changed, failed = apply_tweaks(f)

    assert failed == []
    assert changed["global:window_animation_scale"] == ("1.0", "0.5")
    assert changed["global:transition_animation_scale"] == ("null", "0.5")
    assert "global:animator_duration_scale" not in changed, "already at target: skipped"
    assert f.settings["global/transition_animation_scale"] == "0.5"


def test_apply_tweaks_second_run_changes_nothing():
    f = device()
    apply_tweaks(f)
    f.calls.clear()

    assert apply_tweaks(f) == ({}, [])
    assert not [c for c in f.calls if c.startswith("settings put")]


def test_apply_tweaks_skips_unverified_write():
    f = device()
    f.ignore_settings_writes.add("global/window_animation_scale")

    changed, failed = apply_tweaks(f)

    assert "global:window_animation_scale" not in changed
    assert failed == ["global:window_animation_scale"]
    assert changed["global:transition_animation_scale"] == ("null", "0.5")


def test_tweaks_are_tracked_so_restore_can_reset_them():
    assert set(TWEAKS) <= set(TRACKED_SETTINGS)


def test_tweaks_pin_the_confirmed_keys():
    assert set(TWEAKS) == {
        "global:window_animation_scale",
        "global:transition_animation_scale",
        "secure:limit_ad_tracking",
        "secure:amz_limit_ad_tracking",
        "secure:non_amz_limit_ad_tracking",
        "secure:USAGE_METRICS_UPLOAD_ENABLED",
    }


def test_tweaks_exclude_animator_duration_scale():
    assert "global:animator_duration_scale" not in TWEAKS
    assert "global:animator_duration_scale" in TRACKED_SETTINGS
