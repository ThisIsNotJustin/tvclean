import re
import subprocess
import time
from pathlib import Path
from typing import Callable, Protocol


class AdbError(Exception):
    """An adb command failed."""


class DeviceUnreachable(AdbError):
    """The TV did not answer adb: the device is offline, gone or refusing the connection."""


# Output that means adb lost the device, as opposed to a command that merely failed.
# Matched case-insensitively against stderr and stdout of a nonzero exit.
TRANSPORT_FAILURE_PATTERNS = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"device offline",
        r"no devices/emulators found",
        r"device '[^']*' not found",
        r"device unauthorized",
        r"closed",
        r"failed to connect",
        r"connection refused",
        r"cannot connect",
    )
)


class Adb(Protocol):
    def shell(self, cmd: str) -> str:
        """Run a shell command on the TV and return its output.

        A nonzero exit that is not a transport failure returns stdout and stderr
        combined; pm, am and settings report failure in that output, so callers
        inspect it. A transport failure (device lost) raises DeviceUnreachable.
        """
        ...

    def pull(self, remote: str, local: Path) -> None: ...

    def install(self, apk: Path) -> None: ...

    def reboot(self) -> None: ...

    def wait_ready(self, timeout_s: int = 240) -> None: ...


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def _is_transport_failure(text: str) -> bool:
    return any(p.search(text) for p in TRANSPORT_FAILURE_PATTERNS)


class RealAdb(Adb):
    def __init__(
        self,
        serial: str,
        adb_path: str,
        run: Callable[[list[str]], subprocess.CompletedProcess] = _run,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.serial = serial
        self.adb_path = adb_path
        self._run = run
        self._sleep = sleep

    def _device_cmd(self, *args: str) -> list[str]:
        return [self.adb_path, "-s", self.serial, *args]

    def _checked(self, args: list[str]) -> str:
        result = self._run(args)
        if result.returncode == 0:
            return result.stdout
        text = f"{result.stdout}{result.stderr}".strip() or f"adb failed: {' '.join(args)}"
        if _is_transport_failure(text):
            raise DeviceUnreachable(text)
        raise AdbError(text)

    def shell(self, cmd: str) -> str:
        args = self._device_cmd("shell", cmd)
        result = self._run(args)
        if result.returncode == 0:
            return result.stdout
        text = f"{result.stdout}{result.stderr}"
        if _is_transport_failure(text):
            raise DeviceUnreachable(text.strip())
        return text

    def pull(self, remote: str, local: Path) -> None:
        self._checked(self._device_cmd("pull", remote, str(local)))

    def install(self, apk: Path) -> None:
        self._checked(self._device_cmd("install", "-r", str(apk)))

    def reboot(self) -> None:
        self._checked(self._device_cmd("reboot"))

    def wait_ready(self, timeout_s: int = 240) -> None:
        elapsed = 0
        while True:
            self._run([self.adb_path, "connect", self.serial])
            probe = self._run(self._device_cmd("shell", "getprop", "sys.boot_completed"))
            if probe.returncode == 0 and probe.stdout.strip() == "1":
                return
            if elapsed >= timeout_s:
                raise DeviceUnreachable(f"{self.serial} not ready after {timeout_s}s")
            self._sleep(5)
            elapsed += 5
