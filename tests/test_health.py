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


def test_check_health_reports_netflix_missing():
    adb = FakeAdb({"com.netflix.ninja": {"enabled": False, "path": "/data/app/n.apk"}})
    assert "Netflix has no launchable activity (missing or disabled?)" in check_health(adb)


def test_check_health_reports_netflix_launch_incomplete():
    adb = FakeAdb(NETFLIX, raw_outputs={"am start -W -n com.netflix.ninja/.MainActivity": "Error\n"})
    assert "Netflix did not finish launching" in check_health(adb)


def test_wifi_check_ignores_connected_wifi_outside_current_networks():
    connectivity = (
        "Current Networks:\n"
        "  NetworkAgentInfo{ ni{[type: WIFI[], state: DISCONNECTED/DISCONNECTED]} }\n"
        "\n"
        "Status for known UIDs:\n"
        "  NetworkAgentInfo{ ni{[type: WIFI[], state: CONNECTED/CONNECTED]} }\n"
    )
    adb = FakeAdb(NETFLIX, raw_outputs={"dumpsys connectivity": connectivity})
    assert "Wi-Fi not connected" in check_health(adb)


def test_wifi_check_other_network_connected_wifi_not():
    connectivity = (
        "Current Networks:\n"
        "  NetworkAgentInfo{ ni{[type: ETHERNET[], state: CONNECTED/CONNECTED]} }\n"
        "  NetworkAgentInfo{ ni{[type: WIFI[], state: DISCONNECTED/DISCONNECTED]} }\n"
        "\n"
        "Status for known UIDs:\n"
    )
    adb = FakeAdb(NETFLIX, raw_outputs={"dumpsys connectivity": connectivity})
    assert "Wi-Fi not connected" in check_health(adb)


def test_check_health_propagates_device_unreachable():
    adb = FakeAdb(NETFLIX)
    adb.offline = True
    with pytest.raises(DeviceUnreachable):
        check_health(adb)


def test_wifi_check_handles_crlf_line_endings():
    connectivity = (
        "Current Networks:\r\n"
        "  NetworkAgentInfo{ ni{[type: WIFI[], state: CONNECTED/CONNECTED]} }\r\n"
        "\r\n"
        "Status for known UIDs:\r\n"
    )
    adb = FakeAdb(NETFLIX, raw_outputs={"dumpsys connectivity": connectivity})
    assert check_health(adb) == []


def test_wifi_check_header_with_trailing_whitespace_and_crlf():
    connectivity = (
        "Current Networks: \r\n"
        "  NetworkAgentInfo{ ni{[type: WIFI[], state: CONNECTED/CONNECTED]} }\r\n"
        "\r\n"
        "Status for known UIDs:\r\n"
    )
    adb = FakeAdb(NETFLIX, raw_outputs={"dumpsys connectivity": connectivity})
    assert check_health(adb) == []
