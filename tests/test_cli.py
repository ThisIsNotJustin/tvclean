from datetime import datetime
from pathlib import Path

import pytest

from tests.fakes import FakeAdb
from tvclean import cli, metrics
from tvclean.backup import list_backups
from tvclean.debloat import Report
from tvclean.state import read_state

CATALOG = Path(__file__).parent / "data" / "catalog_ok.toml"
NETFLIX = "com.netflix.ninja"


@pytest.fixture(autouse=True)
def catalog_and_no_settle(monkeypatch):
    monkeypatch.setenv("TVCLEAN_CATALOG", str(CATALOG))
    monkeypatch.setattr(metrics, "IDLE_SETTLE_S", 0)  # the idle wait is real time otherwise


def device() -> FakeAdb:
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

    code_on, _, err_on = run_cli(["feature", "airplay", "on"], f, tmp_path, capsys)
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

    def shell(self, cmd):
        if cmd.startswith("settings get"):
            self.settings_reads += 1
            if self.settings_reads > self.SETTINGS_READS_BEFORE_TWEAKS:
                self.offline = True
        return super().shell(cmd)


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

    code, out, err = run_cli(["debloat", "--tier", "moderate"], f, tmp_path, capsys, input_fn=lambda _: "n")

    backups = list_backups(tmp_path)
    assert code == 1
    assert "refused" in out and "com.safe" in out
    assert "Reverted: com.mod" in out
    assert "Cold launch com.netflix.ninja:" in out
    assert "MemAvailable:" in out
    assert backups[0].name in err
    assert "tvclean restore" in err
