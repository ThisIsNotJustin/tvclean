"""In-memory stand-in for the Fire TV's adb surface.

packages: name -> {"enabled": bool, "path": str}
settings: "namespace/key" -> value
refuse_disable: packages whose `pm disable-user` Fire OS refuses (state unchanged)
unreachable_after_reboot: adb drops off after a reboot until the test ends
healthy: when False, `am start -W` reports the activity as missing
raw_outputs: "full shell command" -> output returned verbatim (models failed commands)
refuse_enable: packages whose `pm enable` Fire OS refuses (state unchanged)
install_error: when set, `install` raises AdbError with this message (non-transport failure)
silent_install: when True, `install` succeeds without listing the package afterwards
split_packages: packages `pm path` reports as split APKs (two `package:` lines)

Only the commands the implemented tasks need are handled. Anything else raises
AssertionError so a test cannot silently rely on unmodelled behaviour.
"""

from pathlib import Path

from tvclean.adb import Adb, AdbError, DeviceUnreachable

# Shell commands that change device state; counted for fail_after_changes.
CHANGING_COMMANDS = ("pm disable-user", "pm enable ", "pm uninstall", "cmd package install-existing")

RESOLVE_HEADER = "priority=0 preferredOrder=0 match=0x108000 specificIndex=-1 isDefault=true\n"

# Shape copied from the TV's `dumpsys connectivity` Wi-Fi line. Only the type and state
# markers are kept; the addresses and SSID in the real line are deliberately left out.
WIFI_CONNECTED_OUTPUT = (
    "Active default network: 100\n"
    "\n"
    "Current Networks:\n"
    "  NetworkAgentInfo{ ni{[type: WIFI[], state: CONNECTED/CONNECTED, reason: (unspecified)]}"
    "  network{100} }\n"
    "    Requests: REQUEST:2 LISTEN:20 BACKGROUND_REQUEST:0 total:22\n"
    "\n"
    "Status for known UIDs:\n"
    "  \n"
)


class FakeAdb(Adb):
    def __init__(
        self,
        packages: dict[str, dict],
        settings: dict[str, str] | None = None,
        mem_available_kb: int = 680000,
        refuse_disable: set[str] = frozenset(),
        unreachable_after_reboot: bool = False,
        healthy: bool = True,
        raw_outputs: dict[str, str] | None = None,
        refuse_enable: set[str] = frozenset(),
        install_error: str | None = None,
        silent_install: bool = False,
        fail_after_changes: int | None = None,
        ignore_settings_writes: set[str] = frozenset(),
        split_packages: set[str] = frozenset(),
    ):
        self.packages = {
            name: {"enabled": spec["enabled"], "path": spec["path"], "installed": True}
            for name, spec in packages.items()
        }
        self.settings = dict(settings or {})
        self.mem_available_kb = mem_available_kb
        self.refuse_disable = set(refuse_disable)
        self.unreachable_after_reboot = unreachable_after_reboot
        self.healthy = healthy
        self.raw_outputs = dict(raw_outputs or {})
        self.refuse_enable = set(refuse_enable)
        self.install_error = install_error
        self.silent_install = silent_install
        self.fail_after_changes = fail_after_changes
        self.ignore_settings_writes = set(ignore_settings_writes)
        self.split_packages = set(split_packages)
        self.changes = 0
        self.calls: list[str] = []
        self.pulled: list[str] = []
        self.installed_apks: list[Path] = []
        self.reboots = 0
        self.offline = False

    # Adb protocol

    def shell(self, cmd: str) -> str:
        self.calls.append(cmd)
        if self.offline:
            raise DeviceUnreachable("device offline")
        if cmd in self.raw_outputs:
            output = self.raw_outputs[cmd]
        else:
            output = self._dispatch(cmd.split())
        if cmd.startswith(CHANGING_COMMANDS):
            self.changes += 1
            if self.fail_after_changes is not None and self.changes >= self.fail_after_changes:
                self.offline = True  # the TV drops off right after this change
        return output

    def pull(self, remote: str, local: Path) -> None:
        self.calls.append(f"pull {remote}")
        self.pulled.append(remote)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(b"fake apk")

    def install(self, apk: Path) -> None:
        self.calls.append(f"install {apk}")
        self.installed_apks.append(apk)
        if self.install_error is not None:
            raise AdbError(self.install_error)
        name = apk.stem
        if self.silent_install:
            return
        self.packages[name] = {
            "enabled": True,
            "path": f"/data/app/{name}/base.apk",
            "installed": True,
        }

    def reboot(self) -> None:
        self.calls.append("reboot")
        self.reboots += 1
        self.offline = self.unreachable_after_reboot

    def wait_ready(self, timeout_s: int = 240) -> None:
        if self.offline:
            raise DeviceUnreachable(f"not ready after {timeout_s}s")

    # Command simulation

    def _dispatch(self, args: list[str]) -> str:
        if args[:2] == ["pm", "list"] and args[2:3] == ["packages"]:
            return self._list_packages(args[3:])
        if args[:2] == ["pm", "path"]:
            return self._pm_path(args[-1])
        if args[:1] == ["pm"] and args[1:2] == ["disable-user"]:
            return self._disable(args[-1])
        if args[:1] == ["pm"] and args[1:2] == ["enable"]:
            return self._enable(args[-1])
        if args[:1] == ["pm"] and args[1:2] == ["uninstall"]:
            return self._uninstall(args[-1])
        if args[:3] == ["cmd", "package", "install-existing"]:
            return self._install_existing(args[-1])
        if args[:1] == ["settings"] and args[1:2] == ["get"]:
            value = self.settings.get(f"{args[2]}/{args[3]}")
            return "null" if value is None else value
        if args[:1] == ["settings"] and args[1:2] == ["put"]:
            key = f"{args[2]}/{args[3]}"
            if key not in self.ignore_settings_writes:
                self.settings[key] = args[4]
            return ""
        if args[:1] == ["settings"] and args[1:2] == ["delete"]:
            key = f"{args[2]}/{args[3]}"
            if key not in self.ignore_settings_writes:
                self.settings.pop(key, None)
            return ""
        if args == ["cat", "/proc/meminfo"]:
            return f"MemTotal:        1500000 kB\nMemAvailable:   {self.mem_available_kb} kB\n"
        if args[:3] == ["cmd", "package", "resolve-activity"]:
            return self._resolve_activity(args)
        if args[:3] == ["am", "start", "-W"]:
            return self._start_activity(args[args.index("-n") + 1])
        if args[:2] == ["am", "force-stop"]:
            return ""
        if args == ["getprop", "sys.boot_completed"]:
            return "1\n"
        if args == ["dumpsys", "tv_input"]:
            return self._tv_input()
        if args == ["dumpsys", "connectivity"]:
            return WIFI_CONNECTED_OUTPUT
        if args == ["input", "keyevent", "KEYCODE_HOME"]:
            return ""
        raise AssertionError(f"FakeAdb: unhandled command: {' '.join(args)}")

    def _tv_input(self) -> str:
        if not self.healthy:
            return "TvInputManagerService\n  inputs: AV1, Antenna\n"
        return (
            "TvInputManagerService\n"
            "  inputs: HDMI1, HDMI2, HDMI3\n"
            "  service: HdmiInputService\n"
        )

    def _list_packages(self, flags: list[str]) -> str:
        names = [n for n, p in self.packages.items() if p["installed"]]
        if "-d" in flags:
            names = [n for n in names if not self.packages[n]["enabled"]]
            return "\n".join(f"package:{n}" for n in names)
        if "-f" in flags:
            return "\n".join(f"package:{self.packages[n]['path']}={n}" for n in names)
        return "\n".join(f"package:{n}" for n in names)

    def _disable(self, name: str) -> str:
        if name not in self.packages:
            return f"Error: Unknown package: {name}"
        if name in self.refuse_disable:
            return f"Exception occurred while executing 'disable-user': Cannot disable {name}"
        self.packages[name]["enabled"] = False
        return f"Package {name} new state: disabled-user"

    def _enable(self, name: str) -> str:
        if name not in self.packages:
            return f"Error: Unknown package: {name}"
        if name in self.refuse_enable:
            return f"Exception occurred while executing 'enable': Cannot enable {name}"
        self.packages[name]["enabled"] = True
        return f"Package {name} new state: enabled"

    def _pm_path(self, name: str) -> str:
        pkg = self.packages.get(name)
        if pkg is None or not pkg["installed"]:
            return ""
        lines = [f"package:{pkg['path']}"]
        if name in self.split_packages:
            lines.append(f"package:/data/app/{name}/split_config.arm64_v8a.apk")
        return "\n".join(lines) + "\n"

    def _uninstall(self, name: str) -> str:
        if name not in self.packages or not self.packages[name]["installed"]:
            return "Failure [not installed for 0]"
        self.packages[name]["installed"] = False
        return "Success"

    def _install_existing(self, name: str) -> str:
        self.packages[name]["installed"] = True
        self.packages[name]["enabled"] = True
        return f"Package {name} installed for user: 0"

    def _resolve_activity(self, args: list[str]) -> str:
        if "android.intent.category.HOME" in args:
            return RESOLVE_HEADER + "com.amazon.tv.launcher/.ui.HomeActivity_vNext\n"
        if "android.settings.SETTINGS" in args:
            return RESOLVE_HEADER + "com.amazon.tv.launcher/.ui.SettingsActivity\n"
        name = args[-1]
        pkg = self.packages.get(name)
        if pkg is None or not pkg["installed"] or not pkg["enabled"]:
            return "No activity found"
        return RESOLVE_HEADER + f"{name}/.MainActivity\n"

    def _start_activity(self, component: str) -> str:
        if not self.healthy:
            return f"Error type 3\nError: Activity class {{{component}}} does not exist."
        return (
            f"Starting: Intent {{ cmp={component} }}\n"
            "Status: ok\n"
            f"Activity: {component}\n"
            "TotalTime: 900\n"
            "WaitTime: 905\n"
            "Complete\n"
        )
