import subprocess
from pathlib import Path

import pytest

import subprocess as _sp

from tvclean.adb import AdbError, DeviceUnreachable, RealAdb


def completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class FakeRun:
    """Scripted adb runner. getprop answers come from `boot_answers` in order."""

    def __init__(self, boot_answers=(), connect_ok=True):
        self.boot_answers = list(boot_answers)
        self.connect_ok = connect_ok
        self.connect_calls = 0
        self.commands = []

    def __call__(self, cmd, timeout=None):
        self.commands.append(cmd)
        if cmd[1:2] == ["connect"]:
            self.connect_calls += 1
            return completed(0 if self.connect_ok else 1, stderr="" if self.connect_ok else "failed to connect")
        if "getprop" in cmd:
            return completed(0, stdout=self.boot_answers.pop(0) if self.boot_answers else "")
        raise AssertionError(f"unexpected command: {cmd}")


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def sleep(self, seconds):
        self.now += seconds


def test_wait_ready_retries_until_boot_completed():
    run = FakeRun(boot_answers=["", "", "1"])
    adb = RealAdb("1.2.3.4:5555", "adb", run=run, sleep=lambda s: None)
    adb.wait_ready(timeout_s=60)
    assert run.connect_calls == 3


def test_wait_ready_raises_device_unreachable_after_timeout():
    run = FakeRun(boot_answers=[""] * 100, connect_ok=False)
    clock = FakeClock()
    adb = RealAdb("1.2.3.4:5555", "adb", run=run, sleep=clock.sleep)
    with pytest.raises(DeviceUnreachable):
        adb.wait_ready(timeout_s=20)
    assert clock.now == 20


def test_shell_raises_adb_error_on_nonzero_transport_failure():
    def run(cmd, timeout=None):
        return completed(1, stderr="error: device offline")

    adb = RealAdb("1.2.3.4:5555", "adb", run=run, sleep=lambda s: None)
    with pytest.raises(AdbError, match="device offline"):
        adb.shell("pm list packages")


def test_commands_target_serial_except_connect():
    seen = []

    def run(cmd, timeout=None):
        seen.append(cmd)
        return completed(0, stdout="1")

    adb = RealAdb("1.2.3.4:5555", "adb", run=run, sleep=lambda s: None)
    adb.wait_ready(timeout_s=60)
    assert seen[0] == ["adb", "connect", "1.2.3.4:5555"]
    assert seen[1] == ["adb", "-s", "1.2.3.4:5555", "shell", "getprop", "sys.boot_completed"]


def _failing(stderr="", stdout="", returncode=1):
    def run(cmd, timeout=None):
        return completed(returncode, stdout=stdout, stderr=stderr)

    return run


def test_shell_device_offline_raises_device_unreachable():
    adb = RealAdb("1.2.3.4:5555", "adb", run=_failing(stderr="error: device offline"), sleep=lambda s: None)
    with pytest.raises(DeviceUnreachable):
        adb.shell("pm list packages")


def test_shell_command_failure_returns_output():
    adb = RealAdb(
        "1.2.3.4:5555",
        "adb",
        run=_failing(stdout="Error: java.lang.SecurityException: Cannot disable"),
        sleep=lambda s: None,
    )
    assert "Cannot disable" in adb.shell("pm disable-user --user 0 com.a")


def test_pull_transport_failure_raises_device_unreachable():
    adb = RealAdb(
        "1.2.3.4:5555",
        "adb",
        run=_failing(stderr="error: device '1.2.3.4:5555' not found"),
        sleep=lambda s: None,
    )
    with pytest.raises(DeviceUnreachable):
        adb.pull("/system/app/a.apk", Path("/tmp/a.apk"))


def test_install_non_transport_failure_raises_plain_adb_error():
    adb = RealAdb(
        "1.2.3.4:5555",
        "adb",
        run=_failing(stderr="Failure [INSTALL_FAILED_VERSION_DOWNGRADE]"),
        sleep=lambda s: None,
    )
    with pytest.raises(AdbError) as info:
        adb.install(Path("/tmp/a.apk"))
    assert not isinstance(info.value, DeviceUnreachable)


def _timing_run(seen, returncode=0, stdout="1"):
    def run(cmd, timeout=None):
        seen.append((cmd, timeout))
        return completed(returncode, stdout=stdout)

    return run


def test_shell_passes_default_timeout_and_custom_timeout():
    seen = []
    adb = RealAdb("1.2.3.4:5555", "adb", run=_timing_run(seen), sleep=lambda s: None)
    adb.shell("pm list packages")
    adb.shell("am start -W -n x/.Y", timeout=180)
    assert seen[0][1] == 120
    assert seen[1][1] == 180


def test_shell_timeout_raises_device_unreachable():
    def run(cmd, timeout=None):
        raise _sp.TimeoutExpired(cmd, timeout)

    adb = RealAdb("1.2.3.4:5555", "adb", run=run, sleep=lambda s: None)
    with pytest.raises(DeviceUnreachable, match="timed out"):
        adb.shell("pm list packages")


def test_reboot_tolerates_link_drop_and_timeout():
    adb = RealAdb("1.2.3.4:5555", "adb", run=_failing(stderr="error: device offline"), sleep=lambda s: None)
    adb.reboot()

    def hangs(cmd, timeout=None):
        raise _sp.TimeoutExpired(cmd, timeout)

    RealAdb("1.2.3.4:5555", "adb", run=hangs, sleep=lambda s: None).reboot()


def test_wait_ready_sleeps_15s_before_first_probe_and_counts_it():
    events = []

    def run(cmd, timeout=None):
        events.append("probe" if "getprop" in cmd else "connect")
        return completed(1 if "getprop" in cmd else 0, stderr="")

    adb = RealAdb("1.2.3.4:5555", "adb", run=run, sleep=lambda s: events.append(("sleep", s)))
    with pytest.raises(DeviceUnreachable):
        adb.wait_ready(timeout_s=30)
    assert events[0] == ("sleep", 15)
    assert events[1] == "connect"
    assert sum(e[1] for e in events if isinstance(e, tuple)) == 30


def test_wait_ready_retries_after_hung_probe():
    calls = {"n": 0}

    def run(cmd, timeout=None):
        if cmd[1:2] == ["connect"]:
            return completed(0)
        calls["n"] += 1
        if calls["n"] == 1:
            raise _sp.TimeoutExpired(cmd, timeout)
        return completed(0, stdout="1\n")

    adb = RealAdb("1.2.3.4:5555", "adb", run=run, sleep=lambda s: None)
    adb.wait_ready(timeout_s=60)
    assert calls["n"] == 2


def test_closed_transport_needs_error_prefix():
    adb = RealAdb("1.2.3.4:5555", "adb", run=_failing(stderr="error: closed"), sleep=lambda s: None)
    with pytest.raises(DeviceUnreachable):
        adb.shell("pm list packages")

    adb = RealAdb(
        "1.2.3.4:5555", "adb",
        run=_failing(stdout="Closed-captioning is disabled\n"), sleep=lambda s: None,
    )
    assert "Closed-captioning" in adb.shell("settings get secure captioning")


def test_connect_ignores_failure():
    run = FakeRun(connect_ok=False)
    adb = RealAdb("1.2.3.4:5555", "adb", run=run, sleep=lambda s: None)
    adb.connect()
    assert run.connect_calls == 1


def test_push_runs_adb_push_for_the_device():
    seen = []

    def run(args, timeout):
        seen.append(args)
        return _sp.CompletedProcess(args, 0, "", "")

    RealAdb("1.2.3.4:5555", "adb", run=run, sleep=lambda s: None).push(
        Path("/tmp/apps.json"), "/sdcard/x/apps.json"
    )
    assert seen == [["adb", "-s", "1.2.3.4:5555", "push", "/tmp/apps.json", "/sdcard/x/apps.json"]]
