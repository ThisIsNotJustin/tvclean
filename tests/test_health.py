import pytest

from tests.fakes import FakeAdb
from tvclean.adb import DeviceUnreachable
from tvclean.health import check_health

NETFLIX = {"com.netflix.ninja": {"enabled": True, "path": "/data/app/n.apk"}}


def test_check_health_ok_on_healthy_fake():
    assert check_health(FakeAdb(NETFLIX)) == []


def test_check_health_reports_missing_hdmi():
    problems = check_health(FakeAdb(NETFLIX, healthy=False))
    assert "HDMI inputs missing" in problems


def test_check_health_reports_wifi_down():
    adb = FakeAdb(
        NETFLIX,
        raw_outputs={
            "dumpsys connectivity": "  NetworkAgentInfo{ ni{[type: WIFI[], state: DISCONNECTED/DISCONNECTED]} }\n"
        },
    )
    assert "Wi-Fi not connected" in check_health(adb)


def test_check_health_reports_boot_not_completed():
    adb = FakeAdb(NETFLIX, raw_outputs={"getprop sys.boot_completed": "0\n"})
    assert any("boot" in p for p in check_health(adb))


def test_check_health_reports_wrong_home_launcher():
    adb = FakeAdb(
        NETFLIX,
        raw_outputs={
            "cmd package resolve-activity --brief -a android.intent.action.MAIN "
            "-c android.intent.category.HOME": "No activity found\n"
        },
    )
    assert any("launcher" in p for p in check_health(adb))


def test_check_health_reports_settings_not_resolvable():
    adb = FakeAdb(
        NETFLIX,
        raw_outputs={
            "cmd package resolve-activity --brief -a android.settings.SETTINGS": "No activity found\n"
        },
    )
    assert any("Settings" in p for p in check_health(adb))


def test_check_health_reports_failed_netflix_launch():
    adb = FakeAdb(NETFLIX, raw_outputs={"am start -W -n com.netflix.ninja/.MainActivity": "Error\n"})
    assert any("Netflix" in p for p in check_health(adb))


def test_check_health_propagates_device_unreachable():
    adb = FakeAdb(NETFLIX)
    adb.offline = True
    with pytest.raises(DeviceUnreachable):
        check_health(adb)
