import pytest

from tests.fakes import FakeAdb


def test_fake_disable_then_list_disabled():
    f = FakeAdb({"com.a": {"enabled": True, "path": "/system/app/a.apk"}})
    f.shell("pm disable-user --user 0 com.a")
    assert "package:com.a" in f.shell("pm list packages -d")


def test_fake_refused_disable_leaves_package_enabled():
    f = FakeAdb({"com.a": {"enabled": True, "path": "/system/app/a.apk"}}, refuse_disable={"com.a"})
    out = f.shell("pm disable-user --user 0 com.a")
    assert "Cannot disable" in out
    assert "package:com.a" not in f.shell("pm list packages -d")


def test_fake_reboot_counts_and_records_order():
    f = FakeAdb({})
    f.shell("settings get global x")
    f.reboot()
    assert f.reboots == 1
    assert f.calls == ["settings get global x", "reboot"]


def test_fake_unreachable_after_reboot_raises_on_wait_ready():
    from tvclean.adb import DeviceUnreachable

    f = FakeAdb({}, unreachable_after_reboot=True)
    f.reboot()
    with pytest.raises(DeviceUnreachable):
        f.wait_ready(timeout_s=10)


def test_fake_unknown_command_raises_assertion():
    f = FakeAdb({})
    with pytest.raises(AssertionError, match="unhandled"):
        f.shell("rm -rf /sdcard")
