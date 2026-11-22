from datetime import datetime

import pytest

from tests.fakes import FakeAdb
from tvclean.backup import list_backups
from tvclean.catalog import Entry
from tvclean.debloat import read_applied, write_applied
from tvclean.features import set_feature
from tvclean.state import read_state

NOW = datetime(2026, 11, 21, 11, 0, 0)


def device() -> FakeAdb:
    return FakeAdb({
        "com.amazon.alexa.app": {"enabled": True, "path": "/system/app/alexa/alexa.apk"},
        "com.other": {"enabled": True, "path": "/system/app/o/o.apk"},
    })


ENTRIES = [
    Entry(package="com.amazon.alexa.app", action="disable", reason="alexa", feature="alexa"),
    Entry(package="com.other", action="disable", reason="core", tier="safe"),
]


def test_feature_off_then_on_roundtrip(tmp_path):
    f = device()
    before = read_state(f)

    set_feature(f, ENTRIES, "alexa", on=False, root=tmp_path, now=lambda: NOW)
    assert not f.packages["com.amazon.alexa.app"]["enabled"]
    assert f.packages["com.other"]["enabled"]

    set_feature(f, ENTRIES, "alexa", on=True, root=tmp_path)
    assert read_state(f) == before


def test_feature_off_updates_applied_json(tmp_path):
    f = device()
    write_applied(tmp_path, {"tier": "safe", "features_off": [], "packages": ["com.keep"]})

    set_feature(f, ENTRIES, "alexa", on=False, root=tmp_path, now=lambda: NOW)

    assert read_applied(tmp_path) == {
        "tier": "safe",
        "features_off": ["alexa"],
        "packages": ["com.amazon.alexa.app", "com.keep"],
    }
    assert len(list_backups(tmp_path)) == 1, "feature off takes a backup first"


def test_feature_on_clears_applied_json(tmp_path):
    f = device()
    set_feature(f, ENTRIES, "alexa", on=False, root=tmp_path, now=lambda: NOW)

    set_feature(f, ENTRIES, "alexa", on=True, root=tmp_path)

    assert read_applied(tmp_path) == {"tier": None, "features_off": [], "packages": []}


def test_feature_unknown_raises(tmp_path):
    f = device()

    with pytest.raises(ValueError):
        set_feature(f, ENTRIES, "bogus", on=False, root=tmp_path, now=lambda: NOW)
    assert f.calls == []
    assert list_backups(tmp_path) == []
