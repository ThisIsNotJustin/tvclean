import subprocess
import time
from pathlib import Path
from typing import Callable, Protocol


class AdbError(Exception):
    """An adb command failed."""


class DeviceUnreachable(AdbError):
    """The TV did not answer adb within the allowed time."""


class Adb(Protocol):
    def shell(self, cmd: str) -> str: ...

    def pull(self, remote: str, local: Path) -> None: ...

    def install(self, apk: Path) -> None: ...

    def reboot(self) -> None: ...

    def wait_ready(self, timeout_s: int = 240) -> None: ...


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


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
        if result.returncode != 0:
            raise AdbError((result.stderr or result.stdout).strip() or f"adb failed: {' '.join(args)}")
        return result.stdout

    def shell(self, cmd: str) -> str:
        return self._checked(self._device_cmd("shell", cmd))

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
