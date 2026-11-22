from datetime import datetime

import pytest

from tests.fakes import FakeAdb
from tvclean.apply import apply_entry, undo_entry
from tvclean.backup import create_backup, list_backups
from tvclean.catalog import Entry
from tvclean.debloat import read_applied, write_applied
from tvclean.restore import NoBackups, run_restore
from tvclean.state import list_installed, read_state

B_PATH = "/data/app/com.b/base.apk"


def device(**settings) -> FakeAdb:
    return FakeAdb(
        {
            "com.a": {"enabled": True, "path": "/system/app/a/a.apk"},
            "com.b": {"enabled": True, "path": B_PATH},
        },
        settings=settings,
    )


def entry(package, action):
    return Entry(package=package, action=action, reason="test", tier="safe")


def test_restore_reenables_and_reinstalls(tmp_path):
    f = device(**{"global/window_animation_scale": "1.0"})
    before = read_state(f)
    backup = create_backup(f, tmp_path, datetime(2026, 11, 21, 9, 0, 0))
    apply_entry(f, entry("com.a", "disable"), read_state(f), backup)
    apply_entry(f, entry("com.b", "uninstall"), read_state(f), backup)
    f.settings["global/window_animation_scale"] = "0.5"

    run_restore(f, tmp_path)

    assert read_state(f) == before


def test_restore_finds_apk_in_older_backup(tmp_path):
    f = device()
    backup1 = create_backup(f, tmp_path, datetime(2026, 11, 21, 9, 0, 0))
    apply_entry(f, entry("com.b", "uninstall"), read_state(f), backup1)
    undo_entry(f, "com.b", backup1)  # reinstall from backup1's APK
    backup2 = create_backup(f, tmp_path, datetime(2026, 11, 21, 10, 0, 0))
    f.shell("pm uninstall --user 0 com.b")  # no APK pulled into backup2

    run_restore(f, tmp_path, name=backup2.name)

    assert "com.b" in list_installed(f)
    assert f.installed_apks[-1] == backup1 / "apks" / "com.b.apk"


def test_restore_no_backups_raises(tmp_path):
    f = device()

    with pytest.raises(NoBackups, match="no backups found in backups/"):
        run_restore(f, tmp_path / "backups")
    assert f.calls == []


def test_restore_resets_settings(tmp_path):
    f = device(**{"global/window_animation_scale": "1.0"})
    backup = create_backup(f, tmp_path, datetime(2026, 11, 21, 9, 0, 0))
    assert list_backups(tmp_path) == [backup]
    f.settings["global/window_animation_scale"] = "0.5"  # changed after the backup
    f.settings["global/animator_duration_scale"] = "0.5"  # was unset in the backup

    run_restore(f, tmp_path)

    assert f.settings["global/window_animation_scale"] == "1.0"
    assert "global/animator_duration_scale" not in f.settings
    assert "settings delete global animator_duration_scale" in f.calls


def test_restore_updates_applied_json(tmp_path):
    f = device()
    backup = create_backup(f, tmp_path, datetime(2026, 11, 21, 9, 0, 0))
    apply_entry(f, entry("com.a", "disable"), read_state(f), backup)
    write_applied(tmp_path, {"tier": "safe", "features_off": [], "packages": ["com.a", "com.keep"]})

    run_restore(f, tmp_path)

    assert read_applied(tmp_path) == {"tier": "safe", "features_off": [], "packages": ["com.keep"]}


def test_restore_continues_after_one_failed_undo(tmp_path):
    f = FakeAdb({
        "com.a": {"enabled": True, "path": "/system/app/a/a.apk"},
        "com.c": {"enabled": True, "path": "/system/app/c/c.apk"},
    })
    backup = create_backup(f, tmp_path, datetime(2026, 11, 21, 9, 0, 0))
    apply_entry(f, entry("com.a", "disable"), read_state(f), backup)
    apply_entry(f, entry("com.c", "disable"), read_state(f), backup)
    write_applied(tmp_path, {"tier": "safe", "features_off": [], "packages": ["com.a", "com.c"]})
    f.refuse_enable.add("com.a")

    outcomes = run_restore(f, tmp_path)

    status = {o.package: o.status for o in outcomes}
    assert status["com.a"] == "failed"
    assert status["com.c"] == "done"
    assert f.packages["com.c"]["enabled"]
    assert read_applied(tmp_path)["packages"] == ["com.a"]


def test_restore_setting_write_ignored_reports_failed(tmp_path):
    f = device(**{"global/window_animation_scale": "1.0"})
    create_backup(f, tmp_path, datetime(2026, 11, 21, 9, 0, 0))
    f.settings["global/window_animation_scale"] = "0.5"
    f.ignore_settings_writes.add("global/window_animation_scale")

    outcomes = run_restore(f, tmp_path)

    status = {o.package: o.status for o in outcomes}
    assert status["global:window_animation_scale"] == "failed"
    assert f.settings["global/window_animation_scale"] == "0.5"


def test_restore_default_targets_oldest_backup(tmp_path):
    f = device(**{"global/window_animation_scale": "1.0"})
    first = read_state(f)
    b1 = create_backup(f, tmp_path, datetime(2026, 11, 21, 9, 0, 0))
    apply_entry(f, entry("com.a", "disable"), read_state(f), b1)
    f.settings["global/window_animation_scale"] = "0.5"
    create_backup(f, tmp_path, datetime(2026, 11, 21, 10, 0, 0))

    run_restore(f, tmp_path)

    assert read_state(f) == first


def test_restore_to_stock_clears_features_off(tmp_path):
    f = device()
    b1 = create_backup(f, tmp_path, datetime(2026, 11, 21, 9, 0, 0))
    apply_entry(f, entry("com.a", "disable"), read_state(f), b1)
    write_applied(tmp_path, {"tier": "safe", "features_off": ["alexa"], "packages": ["com.a"]})

    run_restore(f, tmp_path)

    assert read_applied(tmp_path) == {"tier": None, "features_off": [], "packages": []}


def test_restore_to_stock_drops_applied_packages_already_enabled(tmp_path):
    f = device()
    b1 = create_backup(f, tmp_path, datetime(2026, 11, 21, 9, 0, 0))
    apply_entry(f, entry("com.a", "disable"), read_state(f), b1)
    # com.b was recorded as applied but is installed and enabled now, so it is already at stock.
    write_applied(tmp_path, {"tier": "safe", "features_off": ["alexa"], "packages": ["com.a", "com.b"]})

    run_restore(f, tmp_path)

    assert read_applied(tmp_path) == {"tier": None, "features_off": [], "packages": []}
