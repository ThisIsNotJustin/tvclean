import json
import re
from datetime import datetime
from pathlib import Path

from tvclean.adb import Adb
from tvclean.state import read_state, save_state

BACKUP_NAME = re.compile(r"^\d{8}-\d{6}$")
TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"


def create_backup(
    adb: Adb, root: Path, now: datetime, metrics: dict | None = None
) -> Path:
    """Snapshot device state (and optional metrics) into <root>/<timestamp>/.

    Raises FileExistsError rather than overwriting a backup taken in the same second.
    """
    state = read_state(adb)  # read first: a lost device must not leave a half-made backup
    directory = root / now.strftime(TIMESTAMP_FORMAT)
    directory.mkdir(parents=True)
    (directory / "apks").mkdir()
    save_state(state, directory / "state.json")
    if metrics is not None:
        (directory / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    return directory


def list_backups(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(
        (p for p in root.iterdir() if p.is_dir() and BACKUP_NAME.match(p.name)),
        key=lambda p: p.name,
    )


def latest_backup(root: Path) -> Path | None:
    backups = list_backups(root)
    return backups[-1] if backups else None
