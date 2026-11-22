from tvclean.adb import Adb
from tvclean.metrics import LAUNCH_TARGETS, launch_component, resolved_component, time_launch

HOME_RESOLVE = (
    "cmd package resolve-activity --brief -a android.intent.action.MAIN "
    "-c android.intent.category.HOME"
)
SETTINGS_RESOLVE = "cmd package resolve-activity --brief -a android.settings.SETTINGS"
HOME_PACKAGE_PREFIX = "com.amazon.tv.launcher/"
WIFI_MARKER = "type: WIFI"
WIFI_STATE = "state: CONNECTED/CONNECTED"
CURRENT_NETWORKS_HEADER = "Current Networks:"
HEALTH_LAUNCH_PKG = LAUNCH_TARGETS[0]


def current_networks_section(connectivity: str) -> list[str]:
    """Lines under `Current Networks:` in `dumpsys connectivity`.

    The section runs until the next top-level (unindented) `Name:` header. Anything
    outside it, such as a stale network line in a later section, is ignored.
    """
    lines = connectivity.splitlines()
    try:
        start = lines.index(CURRENT_NETWORKS_HEADER) + 1
    except ValueError:
        return []
    section: list[str] = []
    for line in lines[start:]:
        if line.strip() and not line[0].isspace() and line.rstrip().endswith(":"):
            break
        section.append(line)
    return section


def wifi_connected(connectivity: str) -> bool:
    return any(
        WIFI_MARKER in line and WIFI_STATE in line
        for line in current_networks_section(connectivity)
    )


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

    if not wifi_connected(adb.shell("dumpsys connectivity")):
        problems.append("Wi-Fi not connected")

    component = launch_component(adb, HEALTH_LAUNCH_PKG)
    if component is None:
        problems.append("Netflix has no launchable activity (missing or disabled?)")
    elif time_launch(adb, HEALTH_LAUNCH_PKG, component) is None:
        problems.append("Netflix did not finish launching")

    return problems
