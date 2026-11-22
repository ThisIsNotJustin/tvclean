from datetime import datetime
from pathlib import Path

from tvclean.catalog import Entry
from tests.fakes import FakeAdb
from tvclean.debloat import read_applied, run_debloat, write_applied

NETFLIX = "com.netflix.ninja"


def fake_measure(adb):
    return {"mem_available_kb": adb.mem_available_kb, "cold_launch_ms": {}}


def safe_entries(count: int) -> list[Entry]:
    return [
        Entry(package=f"com.example.safe{i:02d}", action="disable", reason="test", tier="safe")
        for i in range(count)
    ]


def device(count: int = 0, **kwargs) -> FakeAdb:
    packages = {
        f"com.example.safe{i:02d}": {"enabled": True, "path": f"/system/app/s{i}/s{i}.apk"}
        for i in range(count)
    }
    packages[NETFLIX] = {"enabled": True, "path": "/data/app/netflix/base.apk"}
    return FakeAdb(packages, **kwargs)


def clock(start: datetime):
    """A `now` that advances one second per call, so repeated runs get distinct backup dirs."""
    from datetime import timedelta

    state = {"t": start}

    def now() -> datetime:
        current = state["t"]
        state["t"] = current + timedelta(seconds=1)
        return current

    return now


def run(f, entries, root: Path, confirm, now=None, **kwargs):
    kwargs.setdefault("features_off", set())
    return run_debloat(
        f,
        entries,
        tier="safe",
        root=root,
        confirm=confirm,
        now=now or clock(datetime(2026, 11, 21, 10, 0, 0)),
        measure=fake_measure,
        log=lambda _: None,
        **kwargs,
    )


def test_debloat_batches_of_ten_with_reboot_each(tmp_path):
    f = device(23)
    asked = []

    def confirm(prompt):
        asked.append(prompt)
        return True

    report = run(f, safe_entries(23), tmp_path, confirm)

    assert f.reboots == 3
    assert len(asked) == 3
    assert report.stopped_reason is None
    assert report.metrics_after == fake_measure(f)
    assert all(not f.packages[f"com.example.safe{i:02d}"]["enabled"] for i in range(23))


def test_debloat_reverts_batch_when_owner_says_no(tmp_path):
    f = device(23)
    answers = iter([True, False])

    report = run(f, safe_entries(23), tmp_path, lambda _: next(answers))

    for i in range(10):
        assert not f.packages[f"com.example.safe{i:02d}"]["enabled"], "batch 1 stays disabled"
    for i in range(10, 20):
        assert f.packages[f"com.example.safe{i:02d}"]["enabled"], "batch 2 is enabled again"
    for i in range(20, 23):
        assert f.packages[f"com.example.safe{i:02d}"]["enabled"], "batch 3 never applied"
    assert report.stopped_reason is not None
    assert sorted(report.reverted) == [f"com.example.safe{i:02d}" for i in range(10, 20)]


def test_debloat_reverts_batch_on_health_failure(tmp_path):
    f = device(23)

    def confirm(_prompt):
        # Batch 1 passes; the TV goes unhealthy before batch 2's health check.
        f.healthy = False
        return True

    report = run(f, safe_entries(23), tmp_path, confirm)

    for i in range(10):
        assert not f.packages[f"com.example.safe{i:02d}"]["enabled"], "batch 1 stays disabled"
    for i in range(10, 20):
        assert f.packages[f"com.example.safe{i:02d}"]["enabled"], "batch 2 reverted"
    assert report.stopped_reason is not None
    assert "health" in report.stopped_reason
    assert sorted(report.reverted) == [f"com.example.safe{i:02d}" for i in range(10, 20)]
    assert report.metrics_after is None


def test_debloat_stops_when_device_unreachable(tmp_path):
    f = device(23, unreachable_after_reboot=True)
    confirm_calls = []

    report = run(f, safe_entries(23), tmp_path, lambda p: confirm_calls.append(p) or True)

    backup_name = report.backup.name
    assert report.stopped_reason is not None
    assert "tvclean restore" in report.stopped_reason
    assert backup_name in report.stopped_reason
    assert confirm_calls == []
    reboot_at = f.calls.index("reboot")
    assert not [c for c in f.calls[reboot_at + 1:] if c.startswith("pm ")]


def test_debloat_twice_makes_no_changes(tmp_path):
    f = device(5)
    now = clock(datetime(2026, 11, 21, 10, 0, 0))
    run(f, safe_entries(5), tmp_path, lambda _: True, now=now)

    f.calls.clear()
    report = run(f, safe_entries(5), tmp_path, lambda _: True, now=now)

    assert not [c for c in f.calls if c.startswith("pm disable-user")]
    assert f.reboots == 1  # only the first run rebooted
    assert report.stopped_reason is None
    assert all(o.status == "skipped-already" for o in report.outcomes)


def test_debloat_turns_features_off_by_selection(tmp_path):
    features = {"alexa": "com.amazon.alexa.app", "airplay": "com.amazon.airplay", "updates": "com.amazon.updates"}
    f = device(0)
    for pkg in features.values():
        f.packages[pkg] = {"enabled": True, "path": f"/system/app/{pkg}/base.apk", "installed": True}
    entries = [
        Entry(package=pkg, action="disable", reason="feature", feature=name)
        for name, pkg in features.items()
    ]

    run(f, entries, tmp_path, lambda _: True, features_off={"alexa", "airplay", "updates"})

    for pkg in features.values():
        assert not f.packages[pkg]["enabled"], pkg


def test_applied_round_trip(tmp_path):
    assert read_applied(tmp_path) is None
    data = {"tier": "safe", "features_off": ["alexa"], "packages": ["com.example.x"]}
    write_applied(tmp_path, data)
    assert read_applied(tmp_path) == data
