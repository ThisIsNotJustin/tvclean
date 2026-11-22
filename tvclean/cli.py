"""Command-line front end: `tvclean <command>`. Exit 0 on success, 1 on failure, 2 on bad usage."""
import argparse
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Callable

from tvclean.adb import AdbError, DeviceUnreachable, RealAdb
from tvclean.backup import create_backup, list_backups
from tvclean.catalog import FEATURES, CatalogError, load_catalog
from tvclean.config import REPO_ROOT, catalog_path, default_adb_path, default_device
from tvclean.debloat import Report, run_debloat
from tvclean.features import set_feature
from tvclean.metrics import LAUNCH_TARGETS
from tvclean.restore import NoBackups, run_restore
from tvclean.status import build_status, format_status

DEFAULT_ROOT = REPO_ROOT / "backups"
TIERS = ("safe", "moderate")
RESTORE_HELP = (
    "With no NAME, restores to your first backup (the TV as it was before tvclean). "
    "Pass a backup NAME to roll back to that point instead."
)


def _ask(input_fn: Callable[[str], str], prompt: str) -> bool:
    """Owner confirmation: an answer starting with y (any case) is yes. End of input is no."""
    try:
        answer = input_fn(f"{prompt} ")
    except EOFError:
        return False
    return answer.strip().lower().startswith("y")


def _keep_list(text: str) -> set[str]:
    names = {part.strip() for part in text.split(",") if part.strip()}
    unknown = names - set(FEATURES)
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown feature(s) {', '.join(sorted(unknown))}; expected {', '.join(FEATURES)}"
        )
    return names


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tvclean",
        description="Debloat a Fire TV over adb, with backup and restore.",
    )
    parser.add_argument("--device", default=None, help="TV address, e.g. 192.168.1.253:5555 (default: TVCLEAN_DEVICE or the built-in address)")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    sub.add_parser("backup", help="Save the TV's current state (packages, settings) to backups/")

    debloat = sub.add_parser("debloat", help="Disable the catalog's bloat in reboot-checked batches")
    debloat.add_argument("--tier", choices=list(TIERS), default="safe", help="safe (default) or moderate, which adds more apps")
    debloat.add_argument("--keep", type=_keep_list, default=set(), metavar="alexa,airplay,updates", help="comma list of features to leave on (by default all three are turned off)")
    debloat.add_argument("--yes", action="store_true", help="confirm each batch without asking")
    debloat.add_argument("--no-tweaks", action="store_true", help="skip the animation and ad-tracking settings")

    restore = sub.add_parser("restore", help="Put the TV back to a backup", description=RESTORE_HELP, epilog=RESTORE_HELP)
    restore.add_argument("name", nargs="?", default=None, metavar="NAME", help="backup name to restore to (default: the first backup)")

    sub.add_parser("status", help="Show features, disabled packages, memory and any Amazon re-enables")

    feature = sub.add_parser("feature", help="Turn an optional feature off or back on")
    feature.add_argument("name", choices=list(FEATURES))
    feature.add_argument("state", choices=["on", "off"])

    sub.add_parser("backups", help="List backups in backups/")
    return parser


def _print_outcomes(outcomes) -> None:
    for o in outcomes:
        print(f"{o.status:16} {o.package} {o.detail}".rstrip())


def _failed(outcomes) -> int:
    return sum(1 for o in outcomes if o.status in ("failed", "refused"))


def _mem(kb: int | None) -> str:
    return "-" if kb is None else f"{kb // 1024} MB"


def _ms(value: int | None) -> str:
    return "-" if value is None else f"{value} ms"


def _debloat_lines(report: Report) -> list[str]:
    counts = Counter(o.status for o in report.outcomes)
    lines = ["Packages: " + (", ".join(f"{n} {s}" for s, n in sorted(counts.items())) or "none")]
    for o in report.outcomes:
        if o.status not in ("done", "skipped-already"):
            lines.append(f"  {o.status:16} {o.package} {o.detail}".rstrip())
    if report.reverted:
        lines.append("Reverted: " + ", ".join(report.reverted))
    before_ms = report.metrics_before.get("cold_launch_ms", {})
    after = report.metrics_after or {}
    after_ms = after.get("cold_launch_ms", {})
    for pkg in LAUNCH_TARGETS:
        lines.append(f"Cold launch {pkg}: {_ms(before_ms.get(pkg))} -> {_ms(after_ms.get(pkg))}")
    before_mem = report.metrics_before.get("mem_available_kb")
    lines.append(f"MemAvailable: {_mem(before_mem)} -> {_mem(after.get('mem_available_kb'))}")
    lines.append(f"Backup: {report.backup.name}")
    return lines


def main(
    argv: list[str] | None = None,
    adb_factory: Callable = RealAdb,
    root: Path | None = None,
    input_fn: Callable[[str], str] = input,
) -> int:
    args = build_parser().parse_args(argv)
    root = DEFAULT_ROOT if root is None else root
    device = args.device or default_device()

    try:
        if args.command == "backups":
            backups = list_backups(root)
            for backup in backups:
                print(backup.name)
            if not backups:
                print("no backups found in backups/")
            return 0

        adb = adb_factory(device, default_adb_path())

        if args.command == "backup":
            backup = create_backup(adb, root, datetime.now())
            print(f"Backup saved: {backup}")
            return 0

        entries = load_catalog(catalog_path())

        if args.command == "status":
            report = build_status(adb, entries, root)
            if not report.connected:
                print(
                    f"TV not reachable at {device}. Is it on and is ADB debugging enabled?",
                    file=sys.stderr,
                )
                return 1
            print(format_status(report))
            return 0

        if args.command == "feature":
            outcomes = set_feature(adb, entries, args.name, args.state == "on", root)
            _print_outcomes(outcomes)
            failed = _failed(outcomes)
            if failed:
                print(
                    f"{failed} item(s) could not be switched {args.state}. "
                    "Run the command again, or 'tvclean restore' to go back to stock.",
                    file=sys.stderr,
                )
                return 1
            return 0

        if args.command == "restore":
            outcomes = run_restore(adb, root, args.name)
            _print_outcomes(outcomes)
            failed = _failed(outcomes)
            if failed:
                print(
                    f"{failed} item(s) could not be restored. Run 'tvclean restore' again, "
                    'or see "If something goes wrong" in the README.',
                    file=sys.stderr,
                )
                return 1
            return 0

        # debloat
        if args.yes:
            confirm = lambda prompt: True  # noqa: E731
        else:
            confirm = lambda prompt: _ask(input_fn, prompt)  # noqa: E731
        features_off = set(FEATURES) - args.keep
        report = run_debloat(
            adb,
            entries,
            tier=args.tier,
            features_off=features_off,
            root=root,
            confirm=confirm,
            tweaks=not args.no_tweaks,
        )
        for line in _debloat_lines(report):
            print(line)
        if report.stopped_reason:
            print(report.stopped_reason, file=sys.stderr)
            print(
                f"Your backup is {report.backup.name}; run 'tvclean restore' to undo.",
                file=sys.stderr,
            )
            return 1
        return 0

    except DeviceUnreachable:
        print(
            f"TV not reachable at {device}. Is it on and is ADB debugging enabled?",
            file=sys.stderr,
        )
        return 1
    except NoBackups as err:
        print(str(err), file=sys.stderr)
        return 1
    except FileNotFoundError as err:
        print(str(err), file=sys.stderr)
        return 1
    except CatalogError as err:
        print(f"catalog error: {err}", file=sys.stderr)
        return 1
    except AdbError as err:
        print(str(err), file=sys.stderr)
        return 1
