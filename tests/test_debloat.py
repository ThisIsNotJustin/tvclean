import json
from datetime import datetime
from pathlib import Path

import pytest

from tvclean.catalog import Entry
from tests.fakes import FakeAdb
from tvclean.debloat import RECONNECT_PROMPT, read_applied, run_debloat, write_applied

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
    # Tests skip the real waits: no baseline reboot, no settle time, no health retry delay.
    kwargs.setdefault("baseline_reboot", False)
    kwargs.setdefault("settle_s", 0)
    kwargs.setdefault("health_retry_s", 0)
    kwargs.setdefault("sleep", lambda _: None)
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


def names(*indexes: int) -> list[str]:
    return [f"com.example.safe{i:02d}" for i in indexes]


def test_debloat_revert_reboots(tmp_path):
    f = device(23)
    answers = iter([True, False])
    run(f, safe_entries(23), tmp_path, lambda _: next(answers))
    assert f.reboots == 3  # batch 1, batch 2, and the revert of batch 2


def test_debloat_zero_done_chunk_skips_reboot(tmp_path):
    f = device(5, refuse_disable=set(names(*range(5))))
    confirms = []

    report = run(f, safe_entries(5), tmp_path, lambda p: confirms.append(p) or True)

    assert f.reboots == 0
    assert confirms == []
    assert report.stopped_reason is None
    assert all(o.status == "refused" for o in report.outcomes)
    assert report.metrics_after is not None


def test_debloat_refused_does_not_revert(tmp_path):
    f = device(5, refuse_disable={names(2)[0]})
    confirms = []

    report = run(f, safe_entries(5), tmp_path, lambda p: confirms.append(p) or True)

    assert len(confirms) == 1
    assert report.reverted == []
    assert report.stopped_reason is None
    assert f.packages[names(2)[0]]["enabled"], "refused package stays enabled"
    assert not f.packages[names(0)[0]]["enabled"]
    assert report.metrics_after is not None


def test_debloat_unreachable_during_revert_stops_with_restore_hint(tmp_path):
    # 20 disables happen before the revert; the second revert enable drops the TV off.
    f = device(23, fail_after_changes=22)
    answers = iter([True, False])

    report = run(f, safe_entries(23), tmp_path, lambda _: next(answers))

    assert report.stopped_reason is not None
    assert "tvclean restore" in report.stopped_reason
    assert report.backup.name in report.stopped_reason
    assert report.reverted == names(10)
    assert f.reboots == 2, "no reboot after the failed revert"
    applied = read_applied(tmp_path)
    assert names(10)[0] not in applied["packages"]
    assert names(11)[0] in applied["packages"]


def test_debloat_unreachable_mid_apply_records_prior_outcomes(tmp_path):
    f = device(23, fail_after_changes=3)

    report = run(f, safe_entries(23), tmp_path, lambda _: True)

    assert report.stopped_reason is not None
    assert "tvclean restore" in report.stopped_reason
    done = [o.package for o in report.outcomes if o.status == "done"]
    assert done == names(0, 1)
    # The in-flight disable may have landed on the TV before the loss; it is recorded as unknown.
    assert [(o.package, o.status) for o in report.outcomes if o.status == "failed"] == [(names(2)[0], "failed")]
    assert f.reboots == 0
    assert read_applied(tmp_path)["packages"] == names(0, 1)


def test_debloat_unexpected_error_writes_applied_and_reraises(tmp_path):
    from tvclean.debloat import run_debloat as rd

    f = device(23)
    logs = []

    def confirm(_prompt):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        rd(
            f, safe_entries(23), tier="safe", features_off=set(), root=tmp_path,
            confirm=confirm, now=clock(datetime(2026, 11, 21, 10, 0, 0)),
            measure=fake_measure, log=logs.append,
            baseline_reboot=False, settle_s=0, health_retry_s=0, sleep=lambda _: None,
        )

    assert read_applied(tmp_path)["packages"] == names(*range(10))
    assert any("tvclean restore" in line and "Stopped unexpectedly" in line for line in logs)
    data = json.loads((tmp_path / "20261121-100000" / "report.json").read_text())
    assert "Stopped unexpectedly" in data["stopped_reason"]


def test_applied_json_is_cumulative_across_runs(tmp_path):
    extra = "com.example.extra"
    f = device(0)
    f.packages[extra] = {"enabled": True, "path": "/data/app/extra/base.apk", "installed": True}
    entries = [Entry(package=extra, action="uninstall", reason="extra", tier="safe")]
    now = clock(datetime(2026, 11, 21, 10, 0, 0))

    run(f, entries, tmp_path, lambda _: True, now=now)
    assert read_applied(tmp_path)["packages"] == [extra]

    report = run(f, entries, tmp_path, lambda _: True, now=now)
    assert report.outcomes[0].status == "skipped-missing"
    assert read_applied(tmp_path)["packages"] == [extra]


def test_debloat_applies_tweaks_before_first_batch(tmp_path):
    f = device(5)

    run(f, safe_entries(5), tmp_path, lambda _: True)

    first_tweak = f.calls.index("settings put global window_animation_scale 0.5")
    first_disable = next(i for i, c in enumerate(f.calls) if c.startswith("pm disable-user"))
    assert first_tweak < first_disable


def test_debloat_no_tweaks_skips_settings(tmp_path):
    f = device()

    run(f, [], tmp_path, lambda _: True, tweaks=False)

    assert not any(call.startswith("settings put") for call in f.calls)
    assert f.settings == {}


def test_debloat_writes_report_json(tmp_path):
    f = device(5)
    finished = run(f, safe_entries(5), tmp_path / "finished", lambda _: True)

    data = json.loads((finished.backup / "report.json").read_text())
    assert data["outcomes"][0] == {"package": names(0)[0], "status": "done", "detail": ""}
    assert len(data["outcomes"]) == 5
    assert data["reverted"] == []
    assert data["stopped_reason"] is None
    assert data["metrics_before"] == {"mem_available_kb": 680000, "cold_launch_ms": {}}
    assert data["metrics_after"] == {"mem_available_kb": 680000, "cold_launch_ms": {}}

    stopped_device = device(23, unreachable_after_reboot=True)
    stopped = run(stopped_device, safe_entries(23), tmp_path / "stopped", lambda _: True)

    data = json.loads((stopped.backup / "report.json").read_text())
    assert len([o for o in data["outcomes"] if o["status"] == "done"]) == 10
    assert "tvclean restore" in data["stopped_reason"]
    assert data["metrics_after"] is None


def test_debloat_reboots_for_clean_baseline_before_measuring(tmp_path):
    f = device(5)
    measured_at = []
    logs = []

    def measure(adb):
        measured_at.append(adb.reboots)
        return fake_measure(adb)

    run_debloat(
        f, safe_entries(5), tier="safe", features_off=set(), root=tmp_path,
        confirm=lambda _: True, now=clock(datetime(2026, 11, 21, 10, 0, 0)),
        measure=measure, log=logs.append, settle_s=0, health_retry_s=0,
        sleep=lambda _: None,
    )

    assert measured_at[0] == 1, "the baseline is measured after one reboot"
    assert any("clean baseline" in line for line in logs)


def test_debloat_logs_phases_and_plan(tmp_path):
    f = device(12)
    logs = []

    run_debloat(
        f, safe_entries(12), tier="safe", features_off=set(), root=tmp_path,
        confirm=lambda _: True, now=clock(datetime(2026, 11, 21, 10, 0, 0)),
        measure=fake_measure, log=logs.append, baseline_reboot=False,
        settle_s=0, health_retry_s=0, sleep=lambda _: None,
    )

    text = "\n".join(logs)
    assert "12 packages in 2 batches → 2 reboots (about 10 minutes)" in text
    assert "Measuring baseline (the TV will open Netflix, YouTube and Disney+ by itself)…" in text
    assert "Batch 1/2: disabling com.example.safe00, com.example.safe01" in text
    assert "Batch 2/2: disabling" in text
    assert "Rebooting (up to 4 min)…" in text
    assert "Waiting for the TV to settle…" in text
    assert "Running health checks…" in text
    assert "Measuring results…" in text
    plan_at = next(i for i, line in enumerate(logs) if "packages in" in line)
    first_batch = next(i for i, line in enumerate(logs) if line.startswith("Batch 1/2"))
    assert plan_at < first_batch


def test_settle_before_health(tmp_path):
    f = device(5)
    sleeps = []

    run(f, safe_entries(5), tmp_path, lambda _: True, settle_s=45, sleep=sleeps.append)

    assert sleeps[0] == 45


def test_health_retried_before_revert(tmp_path, monkeypatch):
    from tvclean import debloat as debloat_module

    f = device(5)
    real_check = debloat_module.check_health
    results = iter([["HDMI inputs missing"], []])
    monkeypatch.setattr(debloat_module, "check_health", lambda adb: next(results, real_check(adb)))
    sleeps = []

    report = run(f, safe_entries(5), tmp_path, lambda _: True, health_retry_s=30, sleep=sleeps.append)

    assert report.reverted == []
    assert report.stopped_reason is None
    assert sleeps.count(30) == 1
    assert all(not f.packages[f"com.example.safe{i:02d}"]["enabled"] for i in range(5))


def test_health_reverts_only_after_three_failed_attempts(tmp_path, monkeypatch):
    from tvclean import debloat as debloat_module

    f = device(5)
    attempts = []

    def always_bad(adb):
        attempts.append(1)
        return ["HDMI inputs missing"]

    monkeypatch.setattr(debloat_module, "check_health", always_bad)
    sleeps = []

    report = run(f, safe_entries(5), tmp_path, lambda _: True, health_retry_s=30, sleep=sleeps.append)

    assert len(attempts) == 3
    assert sleeps.count(30) == 2
    assert "failed health check" in report.stopped_reason
    assert all(f.packages[f"com.example.safe{i:02d}"]["enabled"] for i in range(5))


def reconnect_toggling(f):
    """A reconnect that does what the owner does: flips ADB Debugging, then answers Enter."""
    calls = []

    def reconnect(prompt):
        calls.append(prompt)
        f.toggle_adb()
        return True

    return reconnect, calls


def test_debloat_reconnect_prompt_after_reboot_continues(tmp_path):
    f = device(23, adb_off_after_reboot=True)
    reconnect, calls = reconnect_toggling(f)

    report = run(f, safe_entries(23), tmp_path, lambda _: True,
                 baseline_reboot=True, reconnect=reconnect)

    assert report.stopped_reason is None
    assert all(not f.packages[f"com.example.safe{i:02d}"]["enabled"] for i in range(23))
    assert f.reboots == 4, "baseline plus three batches"
    assert len(calls) == f.reboots
    assert set(calls) == {RECONNECT_PROMPT}


def test_debloat_reconnect_quit_stops_with_restore_hint(tmp_path):
    f = device(23, adb_off_after_reboot=True)
    answers = iter([False])

    report = run(f, safe_entries(23), tmp_path, lambda _: True,
                 reconnect=lambda _prompt: next(answers))

    assert report.stopped_reason is not None
    assert "tvclean restore" in report.stopped_reason
    assert report.backup.name in report.stopped_reason
    assert (report.backup / "report.json").is_file()
    assert read_applied(tmp_path) is not None


def test_debloat_reconnect_gives_up_after_three_prompts(tmp_path):
    f = device(23, adb_off_after_reboot=True)
    calls = []

    def reconnect(prompt):
        calls.append(prompt)
        return True  # says it reconnected, but never flips the switch

    report = run(f, safe_entries(23), tmp_path, lambda _: True, reconnect=reconnect)

    assert len(calls) == 3
    assert report.stopped_reason is not None
    assert "tvclean restore" in report.stopped_reason


def test_debloat_without_reconnect_keeps_old_behavior(tmp_path):
    f = device(23, adb_off_after_reboot=True)
    confirm_calls = []

    report = run(f, safe_entries(23), tmp_path, lambda p: confirm_calls.append(p) or True)

    assert report.stopped_reason is not None
    assert "tvclean restore" in report.stopped_reason
    assert confirm_calls == []
    assert f.reboots == 1
