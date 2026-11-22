import re
import time
from typing import Callable

from tvclean.adb import Adb, AdbError

LAUNCH_TARGETS: tuple[str, ...] = ("com.netflix.ninja", "com.amazon.firetv.youtube", "com.disney.disneyplus")

# Idle time after boot before MemAvailable is read, so background services settle.
IDLE_SETTLE_S = 60

SNIPPET_CHARS = 200

_MEM_AVAILABLE = re.compile(r"^MemAvailable:\s+(\d+)\s*kB", re.MULTILINE)
_TOTAL_TIME = re.compile(r"TotalTime:\s*(\d+)")


def _snippet(text: str) -> str:
    return text.strip()[:SNIPPET_CHARS]


def mem_available_kb(adb: Adb) -> int:
    output = adb.shell("cat /proc/meminfo")
    match = _MEM_AVAILABLE.search(output)
    if match is None:
        raise AdbError(f"MemAvailable not found in /proc/meminfo output: {_snippet(output)}")
    return int(match.group(1))


def resolved_component(output: str) -> str | None:
    """The component `cmd package resolve-activity --brief` printed, or None if nothing resolved."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines or "/" not in lines[-1]:
        return None
    return lines[-1]


def launch_component(adb: Adb, pkg: str) -> str | None:
    output = adb.shell(
        "cmd package resolve-activity --brief -a android.intent.action.MAIN "
        f"-c android.intent.category.LEANBACK_LAUNCHER {pkg}"
    )
    return resolved_component(output)


def time_launch(adb: Adb, pkg: str, component: str) -> int | None:
    """Force-stop, cold-start `component`, return TotalTime in ms (None if not reported)."""
    try:
        adb.shell(f"am force-stop {pkg}")
        output = adb.shell(f"am start -W -n {component}")
    finally:
        adb.shell("input keyevent KEYCODE_HOME")
    match = _TOTAL_TIME.search(output)
    return int(match.group(1)) if match else None


def cold_launch_ms(adb: Adb, pkg: str) -> int | None:
    component = launch_component(adb, pkg)
    if component is None:
        return None
    return time_launch(adb, pkg, component)


def collect_metrics(adb: Adb, sleep: Callable[[float], None] = time.sleep) -> dict:
    sleep(IDLE_SETTLE_S)
    return {
        "mem_available_kb": mem_available_kb(adb),
        "cold_launch_ms": {pkg: cold_launch_ms(adb, pkg) for pkg in LAUNCH_TARGETS},
    }
