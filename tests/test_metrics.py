import pytest

from tests.fakes import FakeAdb
from tvclean.adb import AdbError
from tvclean.metrics import (
    LAUNCH_TARGETS,
    cold_launch_ms,
    collect_metrics,
    launch_component,
    mem_available_kb,
)


def test_mem_available_parses_meminfo():
    assert mem_available_kb(FakeAdb({}, mem_available_kb=681908)) == 681908


def test_mem_available_missing_raises_with_snippet():
    adb = FakeAdb({}, raw_outputs={"cat /proc/meminfo": "permission denied"})
    with pytest.raises(AdbError, match="permission denied"):
        mem_available_kb(adb)


def test_cold_launch_parses_total_time():
    adb = FakeAdb({"com.netflix.ninja": {"enabled": True, "path": "/data/app/n.apk"}})
    assert cold_launch_ms(adb, "com.netflix.ninja") == 900


def test_cold_launch_runs_force_stop_start_and_home_in_order():
    adb = FakeAdb({"com.netflix.ninja": {"enabled": True, "path": "/data/app/n.apk"}})
    cold_launch_ms(adb, "com.netflix.ninja")
    assert adb.calls == [
        "cmd package resolve-activity --brief -a android.intent.action.MAIN "
        "-c android.intent.category.LEANBACK_LAUNCHER com.netflix.ninja",
        "am force-stop com.netflix.ninja",
        "am start -W -n com.netflix.ninja/.MainActivity",
        "input keyevent KEYCODE_HOME",
    ]


def test_cold_launch_none_when_activity_missing():
    adb = FakeAdb({"com.netflix.ninja": {"enabled": False, "path": "/data/app/n.apk"}})
    assert cold_launch_ms(adb, "com.netflix.ninja") is None


def test_cold_launch_none_when_start_output_has_no_total_time():
    adb = FakeAdb(
        {"com.netflix.ninja": {"enabled": True, "path": "/data/app/n.apk"}},
        healthy=False,
    )
    assert cold_launch_ms(adb, "com.netflix.ninja") is None


def test_launch_component_reads_last_line():
    adb = FakeAdb({"com.netflix.ninja": {"enabled": True, "path": "/data/app/n.apk"}})
    assert launch_component(adb, "com.netflix.ninja") == "com.netflix.ninja/.MainActivity"


def test_launch_component_none_for_disabled_package():
    adb = FakeAdb({"com.netflix.ninja": {"enabled": False, "path": "/data/app/n.apk"}})
    assert launch_component(adb, "com.netflix.ninja") is None


def test_collect_metrics_waits_60s_before_measuring_memory():
    events: list[object] = []
    adb = FakeAdb(
        {pkg: {"enabled": True, "path": f"/data/app/{pkg}.apk"} for pkg in LAUNCH_TARGETS},
        mem_available_kb=700000,
    )
    original_shell = adb.shell

    def recording_shell(cmd: str) -> str:
        if cmd == "cat /proc/meminfo":
            events.append("meminfo")
        return original_shell(cmd)

    adb.shell = recording_shell  # type: ignore[method-assign]

    def fake_sleep(seconds: float) -> None:
        events.append(("sleep", seconds))

    metrics = collect_metrics(adb, sleep=fake_sleep)

    assert events[0] == ("sleep", 60)
    assert events[1] == "meminfo"
    assert metrics == {
        "mem_available_kb": 700000,
        "cold_launch_ms": {pkg: 900 for pkg in LAUNCH_TARGETS},
    }


def test_collect_metrics_reports_none_for_unlaunchable_target():
    adb = FakeAdb({"com.netflix.ninja": {"enabled": True, "path": "/data/app/n.apk"}})
    metrics = collect_metrics(adb, sleep=lambda s: None)
    assert metrics["cold_launch_ms"]["com.netflix.ninja"] == 900
    assert metrics["cold_launch_ms"]["com.amazon.firetv.youtube"] is None
    assert metrics["cold_launch_ms"]["com.disney.disneyplus"] is None
