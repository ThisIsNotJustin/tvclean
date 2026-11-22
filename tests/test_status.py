import json

from tests.fakes import FakeAdb
from tvclean.catalog import Entry
from tvclean.status import build_status, format_status

ENTRIES = [
    Entry(package="com.amazon.alexa.app", action="disable", reason="alexa", feature="alexa"),
    Entry(package="com.airplay", action="disable", reason="airplay", feature="airplay"),
    Entry(package="com.amazon.updates", action="disable", reason="updates", feature="updates"),
    Entry(package="com.safe", action="disable", reason="core", tier="safe"),
]


def write_applied_file(root, packages):
    root.mkdir(parents=True, exist_ok=True)
    (root / "applied.json").write_text(json.dumps({
        "tier": "safe",
        "features_off": [],
        "packages": packages,
    }))


def test_status_reports_drift(tmp_path):
    # com.x was disabled by an earlier debloat, but the TV now shows it enabled again.
    f = FakeAdb(
        {
            "com.x": {"enabled": True, "path": "/system/app/x/x.apk"},
            "com.amazon.updates": {"enabled": True, "path": "/system/app/u/u.apk"},
        },
        raw_outputs={"getprop ro.build.version.name": "Fire OS 7.6.0.1\n"},
    )
    write_applied_file(tmp_path, ["com.x"])

    r = build_status(f, [], tmp_path)
    text = format_status(r)

    assert r.connected is True
    assert "com.x" in r.drift
    assert "tvclean debloat" in text


def test_status_warns_updates_off(tmp_path):
    # Every package of the updates feature is disabled, so the feature is off.
    f = FakeAdb(
        {
            "com.amazon.updates": {"enabled": False, "path": "/system/app/u/u.apk"},
            "com.amazon.alexa.app": {"enabled": True, "path": "/system/app/a/a.apk"},
        },
        raw_outputs={"getprop ro.build.version.name": "Fire OS 7.6.0.1\n"},
    )

    r = build_status(f, ENTRIES, tmp_path)
    text = format_status(r)

    assert r.features["updates"] is False
    assert r.features["alexa"] is True
    assert text.splitlines()[0] == (
        "⚠ Amazon updates are OFF — run 'tvclean feature updates on' to update."
    )


def test_status_feature_on_if_any_entry_enabled_or_installed(tmp_path):
    f = FakeAdb(
        {
            "com.amazon.updates": {"enabled": True, "path": "/system/app/u/u.apk"},
            "com.airplay": {"enabled": False, "path": "/system/app/p/p.apk"},
        },
        raw_outputs={"getprop ro.build.version.name": "Fire OS 7.6.0.1\n"},
    )

    r = build_status(f, ENTRIES, tmp_path)

    assert r.features == {"alexa": False, "airplay": False, "updates": True}
    assert r.disabled == ["com.airplay"]
    assert r.firmware == "Fire OS 7.6.0.1"
    assert r.mem_available_kb == f.mem_available_kb
    assert r.drift == []


def test_status_unreachable_device(tmp_path):
    f = FakeAdb({})
    f.offline = True

    r = build_status(f, ENTRIES, tmp_path)

    assert r.connected is False


NETFLIX = "com.netflix.ninja"


def test_status_lists_disabled_package_names_sorted(tmp_path):
    f = FakeAdb(
        {
            "com.b": {"enabled": False, "path": "/system/app/b/b.apk"},
            "com.a": {"enabled": False, "path": "/system/app/a/a.apk"},
            "com.c": {"enabled": True, "path": "/system/app/c/c.apk"},
        },
        raw_outputs={"getprop ro.build.version.name": "Fire OS 7.6.0.1\n"},
    )

    text = format_status(build_status(f, [], tmp_path))

    assert "Disabled packages: 2" in text
    assert text.index("  com.a") < text.index("  com.b")
    assert "com.c" not in text


def _backup_with_metrics(root, name, mem_mb, netflix_ms):
    directory = root / name
    directory.mkdir(parents=True)
    (directory / "metrics.json").write_text(json.dumps({
        "mem_available_kb": mem_mb * 1024,
        "cold_launch_ms": {NETFLIX: netflix_ms},
    }))
    return directory


def test_status_compares_first_backup_with_latest_report(tmp_path):
    f = FakeAdb(
        {"com.x": {"enabled": True, "path": "/system/app/x/x.apk"}},
        raw_outputs={"getprop ro.build.version.name": "Fire OS 7.6.0.1\n"},
    )
    _backup_with_metrics(tmp_path, "20261121-100000", 480, 1591)
    later = tmp_path / "20261121-110000"
    later.mkdir()
    (later / "report.json").write_text(json.dumps({
        "outcomes": [], "reverted": [], "stopped_reason": None,
        "metrics_before": {}, "metrics_after": {
            "mem_available_kb": 640 * 1024, "cold_launch_ms": {NETFLIX: 900},
        },
    }))

    text = format_status(build_status(f, [], tmp_path))

    assert "Free memory: 480 MB → 640 MB (+160)" in text
    assert "Netflix cold launch: 1591 ms → 900 ms" in text


def test_status_without_report_omits_comparison(tmp_path):
    f = FakeAdb(
        {"com.x": {"enabled": True, "path": "/system/app/x/x.apk"}},
        raw_outputs={"getprop ro.build.version.name": "Fire OS 7.6.0.1\n"},
    )
    _backup_with_metrics(tmp_path, "20261121-100000", 480, 1591)

    text = format_status(build_status(f, [], tmp_path))

    assert "Free memory" not in text
    assert "Netflix cold launch" not in text
