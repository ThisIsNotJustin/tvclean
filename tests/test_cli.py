from datetime import datetime
from pathlib import Path

import pytest

from tests.fakes import FakeAdb
from tvclean import cli, debloat, metrics
from tvclean.config import REPO_ROOT
from tvclean.backup import list_backups
from tvclean.debloat import Report
from tvclean.state import read_state

CATALOG = Path(__file__).parent / "data" / "catalog_ok.toml"
NETFLIX = "com.netflix.ninja"


@pytest.fixture(autouse=True)
def catalog_and_no_settle(monkeypatch):
    monkeypatch.setenv("TVCLEAN_CATALOG", str(CATALOG))
    monkeypatch.setattr(metrics, "IDLE_SETTLE_S", 0)  # the idle wait is real time otherwise
    monkeypatch.setattr(debloat, "SETTLE_S", 0)
    monkeypatch.setattr(debloat, "HEALTH_RETRY_S", 0)


def device(**kwargs) -> FakeAdb:
    return FakeAdb(
        {
            "com.safe": {"enabled": True, "path": "/system/app/s/s.apk"},
            "com.mod": {"enabled": True, "path": "/system/app/m/m.apk"},
            "com.alexa": {"enabled": True, "path": "/system/app/a/a.apk"},
            "com.airplay": {"enabled": True, "path": "/system/app/p/p.apk"},
            "com.amazon.updates": {"enabled": True, "path": "/system/app/u/u.apk"},
            NETFLIX: {"enabled": True, "path": "/data/app/netflix/base.apk"},
        },
        raw_outputs={"getprop ro.build.version.name": "Fire OS 7.6.0.1\n"},
        **kwargs,
    )


def run_cli(argv, f, root, capsys, input_fn=None):
    kwargs = {"root": root, "adb_factory": lambda serial, adb_path: f}
    if input_fn is not None:
        kwargs["input_fn"] = input_fn
    code = cli.main(argv, **kwargs)
    out, err = capsys.readouterr()
    return code, out, err


def test_cli_restore_no_backups_exits_1(tmp_path, capsys):
    code, _, err = run_cli(["restore"], device(), tmp_path / "backups", capsys)

    assert code == 1
    assert "no backups found in backups/" in err


def test_cli_debloat_keep_flag_parses(tmp_path, monkeypatch, capsys):
    seen = {}

    def fake_run_debloat(adb, entries, **kwargs):
        seen.update(kwargs)
        return Report(
            backup=tmp_path / "20261121-100000",
            outcomes=[],
            reverted=[],
            stopped_reason=None,
            metrics_before={"mem_available_kb": 100 * 1024},
            metrics_after={"mem_available_kb": 100 * 1024},
        )

    monkeypatch.setattr(cli, "run_debloat", fake_run_debloat)
    code, _, _ = run_cli(["debloat", "--keep", "alexa", "--yes"], device(), tmp_path, capsys)

    assert code == 0
    assert seen["features_off"] == {"airplay", "updates"}
    assert seen["tier"] == "safe"


def test_cli_debloat_tier_bogus_exits_2(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["debloat", "--tier", "bogus"], root=tmp_path,
                 adb_factory=lambda serial, adb_path: device())

    assert exc.value.code == 2


def test_cli_debloat_unknown_keep_exits_2(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["debloat", "--keep", "bogus"], root=tmp_path,
                 adb_factory=lambda serial, adb_path: device())

    assert exc.value.code == 2


def test_cli_status_unreachable_exits_1(tmp_path, capsys):
    f = device()
    f.offline = True

    code, out, err = run_cli(["--device", "192.168.1.9:5555", "status"], f, tmp_path, capsys)

    assert code == 1
    assert "TV not reachable at 192.168.1.9:5555" in err
    assert out == ""


def test_cli_debloat_yes_finishes_exit_0_and_prints_backup(tmp_path, capsys):
    f = device()

    code, out, err = run_cli(["debloat", "--yes"], f, tmp_path, capsys)

    assert code == 0, err
    backups = list_backups(tmp_path)
    assert len(backups) == 1
    assert backups[0].name in out
    assert not f.packages["com.safe"]["enabled"]
    assert not f.packages["com.alexa"]["enabled"]


def test_cli_feature_airplay_off_then_on_roundtrip(tmp_path, capsys):
    f = device()
    before = read_state(f)

    code_off, _, err_off = run_cli(["feature", "airplay", "off"], f, tmp_path, capsys)
    assert code_off == 0, err_off
    assert not f.packages["com.airplay"]["enabled"]

    code_on, _, err_on = run_cli(["feature", "airplay", "on"], f, tmp_path, capsys, input_fn=lambda p: "n")
    assert code_on == 0, err_on
    assert read_state(f) == before


def test_cli_help_lists_all_subcommands(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])

    assert exc.value.code == 0
    out = capsys.readouterr().out
    for command in ("backup", "debloat", "restore", "status", "feature", "backups"):
        assert command in out


def test_cli_restore_failed_outcome_exits_1(tmp_path, capsys):
    f = device()
    assert run_cli(["backup"], f, tmp_path, capsys)[0] == 0
    # The TV has since disabled com.alexa, and Fire OS refuses to enable it again.
    f.packages["com.alexa"]["enabled"] = False
    f.refuse_enable = {"com.alexa"}

    code, out, err = run_cli(["restore"], f, tmp_path, capsys)

    assert code == 1
    assert "failed" in out
    assert "1 item(s) could not be restored" in err
    assert 'If something goes wrong' in err


def test_cli_feature_refused_exits_1(tmp_path, capsys):
    f = device()
    f.refuse_disable = {"com.airplay"}

    code, out, err = run_cli(["feature", "airplay", "off"], f, tmp_path, capsys)

    assert code == 1
    assert "refused" in out
    assert "1 item(s) could not be switched off" in err


def test_cli_backup_unreachable_shows_friendly_message(tmp_path, capsys):
    f = device()
    f.offline = True

    code, out, err = run_cli(["--device", "192.168.1.9:5555", "backup"], f, tmp_path, capsys)

    assert code == 1
    assert "TV not reachable at 192.168.1.9:5555. Is it on and is ADB debugging enabled?" in err
    assert "shell" not in err and "device offline" not in err
    assert list_backups(tmp_path) == []


def test_cli_feature_unreachable_shows_friendly_message(tmp_path, capsys):
    f = device()
    f.offline = True

    code, out, err = run_cli(["--device", "192.168.1.9:5555", "feature", "airplay", "off"],
                             f, tmp_path, capsys)

    assert code == 1
    assert "TV not reachable at 192.168.1.9:5555. Is it on and is ADB debugging enabled?" in err
    assert "device offline" not in err


class LosesDeviceAfterBackup(FakeAdb):
    """The TV drops off during the tweak step, after the backup has been written.

    read_state reads the tracked settings (7 `settings get` calls) before the backup
    is finished; the next read is the first tweak check, which comes after the backup.
    """

    SETTINGS_READS_BEFORE_TWEAKS = 7

    def __init__(self, packages):
        super().__init__(packages)
        self.settings_reads = 0

    def shell(self, cmd, timeout=None):
        if cmd.startswith("settings get"):
            self.settings_reads += 1
            if self.settings_reads > self.SETTINGS_READS_BEFORE_TWEAKS:
                self.offline = True
        return super().shell(cmd, timeout)


def test_cli_debloat_unreachable_after_backup_names_backup(tmp_path, capsys):
    f = LosesDeviceAfterBackup({"com.safe": {"enabled": True, "path": "/system/app/s/s.apk"}})

    code, out, err = run_cli(["--device", "192.168.1.9:5555", "debloat", "--yes"],
                             f, tmp_path, capsys)

    backups = list_backups(tmp_path)
    assert code == 1
    assert "Lost contact with the TV during debloat" in err
    assert len(backups) == 1
    assert f"Your backup is {backups[0].name}; run 'tvclean restore' to undo." in err
    assert (backups[0] / "report.json").is_file()


def test_cli_debloat_prints_refused_and_reverted(tmp_path, capsys):
    f = device()
    f.refuse_disable = {"com.safe"}

    def start_then_decline(prompt):
        return "y" if prompt.startswith("Start?") else "n"

    code, out, err = run_cli(
        ["debloat", "--tier", "moderate"], f, tmp_path, capsys, input_fn=start_then_decline
    )

    backups = list_backups(tmp_path)
    assert code == 1
    assert "refused" in out and "com.safe" in out
    assert "Reverted: com.mod" in out
    assert "Cold launch com.netflix.ninja:" in out
    assert "MemAvailable:" in out
    assert backups[0].name in err
    assert "tvclean restore" in err


def test_cli_debloat_declined_start_changes_nothing(tmp_path, capsys):
    f = device()
    prompts = []

    def decline(prompt):
        prompts.append(prompt)
        return "n"

    code, out, err = run_cli(["debloat"], f, tmp_path, capsys, input_fn=decline)

    assert code == 0
    assert prompts[0].startswith("Start? [y/N]")
    assert "Not started" in out
    assert list_backups(tmp_path) == []
    assert f.reboots == 0
    assert f.packages["com.safe"]["enabled"]


def test_cli_ctrl_c_prints_backup_and_exits_130(tmp_path, capsys):
    f = device()

    def ctrl_c_after_start(prompt):
        if prompt.startswith("Start?"):
            return "y"
        raise KeyboardInterrupt

    code, out, err = run_cli(["debloat"], f, tmp_path, capsys, input_fn=ctrl_c_after_start)

    backups = list_backups(tmp_path)
    assert code == 130
    assert len(backups) == 1
    assert f"Stopped. Your backup is {backups[0].name}; run 'tvclean restore' to undo." in err


@pytest.mark.parametrize("argv", [
    ["feature", "airplay", "off"],
    ["restore"],
    ["debloat", "--yes"],
])
def test_cli_refuses_changing_command_on_wrong_tv(tmp_path, capsys, argv):
    f = device()
    f.device_name = "mido"

    code, out, err = run_cli(argv, f, tmp_path, capsys)

    assert code == 1
    assert "Connected device is mido, not this TV (ginza). Check --device." in err
    assert f.reboots == 0
    assert f.packages["com.airplay"]["enabled"]


def test_cli_connects_once_at_startup(tmp_path, capsys):
    class Spy(FakeAdb):
        connects = 0

        def connect(self):
            Spy.connects += 1

    f = Spy(
        {"com.safe": {"enabled": True, "path": "/system/app/s/s.apk"}},
        raw_outputs={"getprop ro.build.version.name": "Fire OS 7.6.0.1\n"},
    )
    run_cli(["status"], f, tmp_path, capsys)

    assert Spy.connects == 1


def test_cli_debloat_reconnect_prompt_reads_enter_and_q(tmp_path, capsys):
    f = device(adb_off_after_reboot=True)
    answers = iter(["", "q"])
    prompts = []

    def input_fn(prompt):
        prompts.append(prompt)
        f.toggle_adb()  # the owner flips ADB Debugging before answering
        return next(answers)

    code, _, err = run_cli(["debloat", "--yes"], f, tmp_path, capsys, input_fn=input_fn)

    assert code == 1
    assert len(prompts) == 2, "baseline reboot, then the first batch's reboot"
    assert all(debloat.RECONNECT_PROMPT in p for p in prompts)
    assert "tvclean restore" in err


def test_cli_debloat_reconnect_enter_continues_exit_0(tmp_path, capsys):
    f = device(adb_off_after_reboot=True)
    prompts = []

    def input_fn(prompt):
        prompts.append(prompt)
        f.toggle_adb()
        return ""

    code, _, err = run_cli(["debloat", "--yes"], f, tmp_path, capsys, input_fn=input_fn)

    assert code == 0, err
    assert prompts and len(prompts) == f.reboots
    assert all(debloat.RECONNECT_PROMPT in p for p in prompts)


HOME_PKG = "dev.tvclean.home"
HOME_SERVICE = "dev.tvclean.home/dev.tvclean.home.RedirectService"
BUILD_HINT = "Build it first: cd home && ./gradlew assembleRelease"


def home_tv(services=None, enabled=None, installed=True) -> FakeAdb:
    f = device()
    if installed:
        f.packages[HOME_PKG] = {"enabled": True, "path": "/data/app/home/base.apk", "installed": True}
    if services is not None:
        f.settings["secure/enabled_accessibility_services"] = services
    if enabled is not None:
        f.settings["secure/accessibility_enabled"] = enabled
    return f


def test_cli_home_status_prints_state(tmp_path, capsys):
    f = home_tv(services=HOME_SERVICE, enabled="1")
    f.grants.add("android.permission.WRITE_SECURE_SETTINGS")
    f.appops[f"{HOME_PKG} GET_USAGE_STATS"] = "allow"

    code, out, err = run_cli(["home", "status"], f, tmp_path, capsys)

    assert code == 0, err
    assert "Installed: yes" in out
    assert "Version: 1.0" in out
    assert "Redirect: on" in out
    assert "WRITE_SECURE_SETTINGS: granted" in out
    assert "Usage access: allowed" in out


def test_cli_home_status_when_not_installed(tmp_path, capsys):
    code, out, _ = run_cli(["home", "status"], home_tv(installed=False), tmp_path, capsys)

    assert code == 0
    assert "Installed: no" in out


def test_cli_home_install_missing_apk_exits_1(tmp_path, capsys):
    f = home_tv(installed=False)

    code, _, err = run_cli(["home", "install", "--apk", str(tmp_path / "missing.apk")], f, tmp_path, capsys)

    assert code == 1
    assert BUILD_HINT in err
    assert not any(c.startswith("install") for c in f.calls)


def test_cli_home_install_runs_and_turns_redirect_on(tmp_path, capsys):
    apk = tmp_path / "dev.tvclean.home.apk"
    apk.write_bytes(b"apk")
    f = home_tv(installed=False)

    code, _, err = run_cli(["home", "install", "--apk", str(apk)], f, tmp_path, capsys)

    assert code == 0, err
    assert f.settings["secure/accessibility_enabled"] == "1"
    assert f.grants == {"android.permission.WRITE_SECURE_SETTINGS"}


def test_cli_home_on_refuses_wrong_device(tmp_path, capsys):
    f = home_tv()
    f.device_name = "mido"

    code, _, err = run_cli(["home", "on"], f, tmp_path, capsys)

    assert code == 1
    assert "Connected device is mido, not this TV (ginza). Check --device." in err
    assert "secure/enabled_accessibility_services" not in f.settings


def test_cli_home_apps_invalid_pushes_nothing(tmp_path, capsys):
    bad = tmp_path / "apps.json"
    bad.write_text('{"version": 1, "apps": []}')
    f = home_tv()

    code, _, err = run_cli(["home", "apps", str(bad)], f, tmp_path, capsys)

    assert code == 1
    assert "apps.json invalid: empty apps array" in err
    assert f.pushes == []
    assert f.calls == []


def test_cli_home_apps_valid_pushes(tmp_path, capsys):
    good = tmp_path / "apps.json"
    good.write_text((REPO_ROOT / "home/app/src/main/assets/apps.json").read_text())
    f = home_tv()

    code, _, err = run_cli(["home", "apps", str(good)], f, tmp_path, capsys)

    assert code == 0, err
    assert [remote for _, remote in f.pushes] == [
        "/sdcard/Android/data/dev.tvclean.home/files/apps.json"
    ]


def airplay_off(f, tmp_path, capsys):
    code, _, err = run_cli(["feature", "airplay", "off"], f, tmp_path, capsys)
    assert code == 0, err


def test_feature_airplay_on_offers_reboot_and_restarts(tmp_path, capsys):
    f = device()
    airplay_off(f, tmp_path, capsys)
    prompts = []

    def answer(prompt):
        prompts.append(prompt)
        return "y"

    code, out, err = run_cli(["feature", "airplay", "on"], f, tmp_path, capsys, input_fn=answer)

    assert code == 0, err
    assert prompts == ["AirPlay starts after a restart. Restart the TV now? [y/N] "]
    assert f.reboots == 1
    assert "TV restarted. AirPlay should be available now." in out


def test_feature_airplay_on_reboot_waits_for_adb_toggle(tmp_path, capsys):
    f = device()
    airplay_off(f, tmp_path, capsys)
    f.adb_off_after_reboot = True
    prompts = []

    def answer(prompt):
        prompts.append(prompt)
        if prompt.startswith("AirPlay starts"):
            return "y"
        f.toggle_adb()
        return ""

    code, out, err = run_cli(["feature", "airplay", "on"], f, tmp_path, capsys, input_fn=answer)

    assert code == 0, err
    assert any(p.startswith("The TV isn't accepting adb") for p in prompts)
    assert "TV restarted. AirPlay should be available now." in out


def test_feature_airplay_on_declined_reboot(tmp_path, capsys):
    f = device()
    airplay_off(f, tmp_path, capsys)

    code, out, err = run_cli(["feature", "airplay", "on"], f, tmp_path, capsys, input_fn=lambda p: "n")

    assert code == 0, err
    assert f.reboots == 0
    assert "AirPlay will start after the next restart." in out


def test_feature_updates_on_does_not_offer_reboot(tmp_path, capsys):
    f = device()
    code, _, err = run_cli(["feature", "updates", "off"], f, tmp_path, capsys)
    assert code == 0, err

    def must_not_ask(prompt):
        raise AssertionError(f"unexpected prompt: {prompt}")

    code, _, err = run_cli(["feature", "updates", "on"], f, tmp_path, capsys, input_fn=must_not_ask)

    assert code == 0, err
    assert f.reboots == 0


def test_cli_home_install_grant_failure_exits_1(tmp_path, capsys):
    apk = tmp_path / "dev.tvclean.home.apk"
    apk.write_bytes(b"apk")
    f = home_tv(installed=False)
    f.raw_outputs[f"pm grant {HOME_PKG} android.permission.WRITE_SECURE_SETTINGS"] = "Exception occurred while executing 'grant'\n"

    code, _, err = run_cli(["home", "install", "--apk", str(apk)], f, tmp_path, capsys)

    assert code == 1
    assert "Could not grant WRITE_SECURE_SETTINGS" in err


def test_cli_home_on_ignored_write_exits_1(tmp_path, capsys):
    f = home_tv(services="", enabled="0")
    f.ignore_settings_writes = {"secure/enabled_accessibility_services"}

    code, out, err = run_cli(["home", "on"], f, tmp_path, capsys)

    assert code == 1
    assert "Could not turn the Home redirect on: the TV did not accept the setting." in err
    assert "Home redirect: on" not in out


def test_cli_home_apps_missing_file_exits_1(tmp_path, capsys):
    f = home_tv()

    code, _, err = run_cli(["home", "apps", str(tmp_path / "nope.json")], f, tmp_path, capsys)

    assert code == 1
    assert "apps.json not found:" in err
    assert f.pushes == []
    assert f.calls == []
