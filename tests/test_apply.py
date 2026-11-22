from pathlib import Path

import pytest

from tests.fakes import FakeAdb
from tvclean.adb import AdbError, DeviceUnreachable
from tvclean.apply import Outcome, apply_entry, undo_entry
from tvclean.catalog import Entry
from tvclean.state import read_state


def entry(package, action="disable"):
    return Entry(package=package, action=action, reason="test", tier="safe")


def test_apply_disable_done():
    f = FakeAdb({"com.x": {"enabled": True, "path": "/system/app/x/x.apk"}})
    out = apply_entry(f, entry("com.x"), read_state(f), Path("unused"))
    assert out == Outcome(package="com.x", status="done")
    assert "package:com.x" in f.shell("pm list packages -d")


def test_apply_disable_skipped_already():
    f = FakeAdb({"com.x": {"enabled": False, "path": "/system/app/x/x.apk"}})
    before = len(f.calls)
    out = apply_entry(f, entry("com.x"), read_state(f), Path("unused"))
    assert out.status == "skipped-already"
    assert not any(c.startswith("pm disable-user") for c in f.calls[before:])


def test_apply_missing_package_is_skipped_missing():
    f = FakeAdb({"com.other": {"enabled": True, "path": "/system/app/o/o.apk"}})
    out = apply_entry(f, entry("com.absent"), read_state(f), Path("unused"))
    assert out == Outcome(package="com.absent", status="skipped-missing")
    assert not any(c.startswith("pm ") and "com.absent" in c for c in f.calls)


def test_apply_refused_disable_reports_refused():
    f = FakeAdb(
        {"com.x": {"enabled": True, "path": "/system/app/x/x.apk"}},
        refuse_disable={"com.x"},
    )
    out = apply_entry(f, entry("com.x"), read_state(f), Path("unused"))
    assert out.status == "refused"
    assert "Cannot disable" in out.detail
    assert "package:com.x" not in f.shell("pm list packages -d")


def test_apply_uninstall_pulls_apk_before_uninstall(tmp_path):
    path = "/data/app/com.x/base.apk"
    f = FakeAdb({"com.x": {"enabled": True, "path": path}})
    out = apply_entry(f, entry("com.x", "uninstall"), read_state(f), tmp_path)
    assert out.status == "done"
    assert (tmp_path / "apks" / "com.x.apk").is_file()
    pull_index = f.calls.index(f"pull {path}")
    uninstall_index = f.calls.index("pm uninstall --user 0 com.x")
    assert pull_index < uninstall_index
    assert "com.x" not in f.shell("pm list packages")


def test_apply_uninstall_refuses_system_path(tmp_path):
    f = FakeAdb({"com.x": {"enabled": True, "path": "/system/app/x/x.apk"}})
    out = apply_entry(f, entry("com.x", "uninstall"), read_state(f), tmp_path)
    assert out == Outcome(package="com.x", status="refused", detail="system package; use disable")
    assert f.pulled == []
    assert not any(c.startswith("pm uninstall") for c in f.calls)


def test_apply_uninstall_pull_failure_is_failed_without_uninstall(tmp_path, monkeypatch):
    f = FakeAdb({"com.x": {"enabled": True, "path": "/data/app/com.x/base.apk"}})

    def broken_pull(remote, local):
        raise AdbError("pull failed: permission denied")

    monkeypatch.setattr(f, "pull", broken_pull)
    out = apply_entry(f, entry("com.x", "uninstall"), read_state(f), tmp_path)
    assert out.status == "failed"
    assert "permission denied" in out.detail
    assert not any(c.startswith("pm uninstall") for c in f.calls)
    assert "com.x" in f.shell("pm list packages")


def test_apply_propagates_device_unreachable(tmp_path, monkeypatch):
    f = FakeAdb({"com.x": {"enabled": True, "path": "/data/app/com.x/base.apk"}})

    def lost_pull(remote, local):
        raise DeviceUnreachable("device offline")

    monkeypatch.setattr(f, "pull", lost_pull)
    with pytest.raises(DeviceUnreachable):
        apply_entry(f, entry("com.x", "uninstall"), read_state(f), tmp_path)


def test_undo_reinstalls_from_pulled_apk(tmp_path):
    f = FakeAdb({"com.x": {"enabled": True, "path": "/data/app/com.x/base.apk"}})
    apks = tmp_path / "apks"
    apks.mkdir()
    (apks / "com.x.apk").write_bytes(b"apk")
    f.shell("pm uninstall --user 0 com.x")
    out = undo_entry(f, "com.x", tmp_path)
    assert out == Outcome(package="com.x", status="done")
    assert f.installed_apks == [apks / "com.x.apk"]
    assert "com.x" in f.shell("pm list packages")


def test_undo_uninstalled_without_apk_uses_install_existing(tmp_path):
    f = FakeAdb({"com.x": {"enabled": True, "path": "/system/app/x/x.apk"}})
    f.shell("pm uninstall --user 0 com.x")
    out = undo_entry(f, "com.x", tmp_path)
    assert out == Outcome(package="com.x", status="done")
    assert "cmd package install-existing com.x" in f.calls
    assert "com.x" in f.shell("pm list packages")


def test_undo_enables_disabled(tmp_path):
    f = FakeAdb({"com.x": {"enabled": False, "path": "/system/app/x/x.apk"}})
    out = undo_entry(f, "com.x", tmp_path)
    assert out == Outcome(package="com.x", status="done")
    assert "pm enable com.x" in f.calls
    assert "package:com.x" not in f.shell("pm list packages -d")


def test_undo_already_fine_is_skipped_already(tmp_path):
    f = FakeAdb({"com.x": {"enabled": True, "path": "/system/app/x/x.apk"}})
    out = undo_entry(f, "com.x", tmp_path)
    assert out == Outcome(package="com.x", status="skipped-already")


def test_undo_install_failure_returns_failed(tmp_path):
    f = FakeAdb(
        {"com.x": {"enabled": True, "path": "/data/app/com.x/base.apk"}},
        install_error="INSTALL_FAILED_VERSION_DOWNGRADE",
    )
    apks = tmp_path / "apks"
    apks.mkdir()
    (apks / "com.x.apk").write_bytes(b"apk")
    f.shell("pm uninstall --user 0 com.x")
    out = undo_entry(f, "com.x", tmp_path)
    assert out.status == "failed"
    assert "INSTALL_FAILED_VERSION_DOWNGRADE" in out.detail
    assert "com.x" not in f.shell("pm list packages")


def test_undo_enable_not_effective_returns_failed(tmp_path):
    f = FakeAdb(
        {"com.x": {"enabled": False, "path": "/system/app/x/x.apk"}},
        refuse_enable={"com.x"},
    )
    out = undo_entry(f, "com.x", tmp_path)
    assert out.status == "failed"
    assert "Cannot enable" in out.detail
    assert "package:com.x" in f.shell("pm list packages -d")


def test_undo_install_not_listed_afterwards_returns_failed(tmp_path):
    f = FakeAdb(
        {"com.x": {"enabled": True, "path": "/data/app/com.x/base.apk"}},
        silent_install=True,
    )
    apks = tmp_path / "apks"
    apks.mkdir()
    (apks / "com.x.apk").write_bytes(b"apk")
    f.shell("pm uninstall --user 0 com.x")
    out = undo_entry(f, "com.x", tmp_path)
    assert out.status == "failed"
    assert "com.x" in out.detail
