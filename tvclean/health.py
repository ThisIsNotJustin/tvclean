from tvclean.adb import Adb
from tvclean.metrics import cold_launch_ms, resolved_component

HOME_RESOLVE = (
    "cmd package resolve-activity --brief -a android.intent.action.MAIN "
    "-c android.intent.category.HOME"
)
SETTINGS_RESOLVE = "cmd package resolve-activity --brief -a android.settings.SETTINGS"
HOME_PACKAGE_PREFIX = "com.amazon.tv.launcher/"
WIFI_MARKER = "type: WIFI"
WIFI_STATE = "state: CONNECTED/CONNECTED"
HEALTH_LAUNCH_PKG = "com.netflix.ninja"


def check_health(adb: Adb) -> list[str]:
    """Problems found on the TV after a batch. An empty list means healthy."""
    problems: list[str] = []

    if adb.shell("getprop sys.boot_completed").strip() != "1":
        problems.append("device has not finished booting")

    if HOME_PACKAGE_PREFIX not in adb.shell(HOME_RESOLVE):
        problems.append("home launcher is not the Amazon launcher")

    if resolved_component(adb.shell(SETTINGS_RESOLVE)) is None:
        problems.append("Settings activity does not resolve")

    if "HdmiInputService" not in adb.shell("dumpsys tv_input"):
        problems.append("HDMI inputs missing")

    connectivity = adb.shell("dumpsys connectivity")
    if not any(WIFI_MARKER in line and WIFI_STATE in line for line in connectivity.splitlines()):
        problems.append("Wi-Fi not connected")

    if cold_launch_ms(adb, HEALTH_LAUNCH_PKG) is None:
        problems.append("Netflix cold launch failed")

    return problems
