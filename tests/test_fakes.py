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


def test_fake_pull_writes_placeholder_file_and_creates_parents(tmp_path):
    f = FakeAdb({"com.a": {"enabled": True, "path": "/data/app/com.a/base.apk"}})
    local = tmp_path / "apks" / "com.a.apk"
    f.pull("/data/app/com.a/base.apk", local)
    assert local.is_file()
    assert f.pulled == ["/data/app/com.a/base.apk"]


def test_fake_install_marks_package_installed_and_enabled(tmp_path):
    f = FakeAdb({"com.a": {"enabled": True, "path": "/data/app/com.a/base.apk"}})
    apk = tmp_path / "com.b.apk"
    apk.write_bytes(b"x")
    f.install(apk)
    assert "com.b" in f.shell("pm list packages")
    assert "package:com.b" not in f.shell("pm list packages -d")
    assert "package:/data/app/com.b/base.apk=com.b" in f.shell("pm list packages -f")


def test_fake_disable_unknown_package_returns_error_output():
    f = FakeAdb({})
    assert f.shell("pm disable-user --user 0 com.nope") == "Error: Unknown package: com.nope"


def test_fake_enable_unknown_package_returns_error_output():
    f = FakeAdb({})
    assert f.shell("pm enable com.nope") == "Error: Unknown package: com.nope"


def test_fake_uninstall_unknown_package_returns_failure():
    f = FakeAdb({})
    assert f.shell("pm uninstall --user 0 com.nope") == "Failure [not installed for 0]"
