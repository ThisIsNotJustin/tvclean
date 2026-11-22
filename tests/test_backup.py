import json
from datetime import datetime

import pytest

from tests.fakes import FakeAdb
from tvclean.backup import create_backup, latest_backup, list_backups


def _adb():
    return FakeAdb({"com.a": {"enabled": True, "path": "/system/app/a/a.apk"}})


def test_create_backup_layout(tmp_path):
    d = create_backup(
        _adb(), tmp_path, datetime(2026, 11, 21, 18, 5, 9), metrics={"mem_available_kb": 1}
    )
    assert d.name == "20261121-180509"
    assert (d / "state.json").exists()
    assert (d / "apks").is_dir()
    assert json.loads((d / "metrics.json").read_text()) == {"mem_available_kb": 1}
    assert latest_backup(tmp_path) == d


def test_create_backup_without_metrics_writes_no_metrics_file(tmp_path):
    d = create_backup(_adb(), tmp_path, datetime(2026, 11, 21, 18, 5, 9))
    assert not (d / "metrics.json").exists()
    assert (d / "state.json").exists()


def test_create_backup_state_matches_device(tmp_path):
    from tvclean.state import load_state

    d = create_backup(_adb(), tmp_path, datetime(2026, 11, 21, 18, 5, 9))
    assert "com.a" in load_state(d / "state.json").installed


def test_create_backup_refuses_to_overwrite_existing_backup(tmp_path):
    now = datetime(2026, 11, 21, 18, 5, 9)
    create_backup(_adb(), tmp_path, now)
    with pytest.raises(FileExistsError):
        create_backup(_adb(), tmp_path, now)


def test_latest_backup_none_when_empty(tmp_path):
    assert latest_backup(tmp_path) is None


def test_latest_backup_none_when_root_missing(tmp_path):
    assert latest_backup(tmp_path / "absent") is None


def test_list_backups_oldest_first(tmp_path):
    a = create_backup(_adb(), tmp_path, datetime(2026, 11, 21, 9, 0, 0))
    b = create_backup(_adb(), tmp_path, datetime(2026, 11, 21, 10, 0, 0))
    c = create_backup(_adb(), tmp_path, datetime(2026, 11, 22, 8, 0, 0))
    assert list_backups(tmp_path) == [a, b, c]
    assert latest_backup(tmp_path) == c


def test_list_backups_ignores_non_backup_entries(tmp_path):
    d = create_backup(_adb(), tmp_path, datetime(2026, 11, 21, 9, 0, 0))
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "scratch").mkdir()
    assert list_backups(tmp_path) == [d]


def test_failed_state_read_leaves_no_backup_behind(tmp_path):
    from tvclean.adb import DeviceUnreachable

    adb = _adb()
    adb.offline = True
    with pytest.raises(DeviceUnreachable):
        create_backup(adb, tmp_path, datetime(2026, 11, 21, 18, 5, 9))
    assert list_backups(tmp_path) == []
