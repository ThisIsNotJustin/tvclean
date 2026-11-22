import os
from pathlib import Path

DEFAULT_DEVICE = "192.168.1.253:5555"

REPO_ROOT = Path(__file__).resolve().parent.parent


def default_adb_path() -> str:
    return os.environ.get("TVCLEAN_ADB", str(Path.home() / "Library/Android/sdk/platform-tools/adb"))


def default_device() -> str:
    return os.environ.get("TVCLEAN_DEVICE", DEFAULT_DEVICE)


def catalog_path() -> Path:
    override = os.environ.get("TVCLEAN_CATALOG")
    if override:
        return Path(override)
    return REPO_ROOT / "data" / "packages.toml"
