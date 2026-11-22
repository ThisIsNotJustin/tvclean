from pathlib import Path

from tvclean import config


def test_catalog_path_defaults_to_repo_data_dir(monkeypatch):
    monkeypatch.delenv("TVCLEAN_CATALOG", raising=False)
    assert config.catalog_path() == Path(config.__file__).resolve().parent.parent / "data" / "packages.toml"


def test_catalog_path_honours_env(monkeypatch, tmp_path):
    monkeypatch.setenv("TVCLEAN_CATALOG", str(tmp_path / "x.toml"))
    assert config.catalog_path() == tmp_path / "x.toml"


def test_device_and_adb_defaults(monkeypatch):
    monkeypatch.delenv("TVCLEAN_DEVICE", raising=False)
    monkeypatch.delenv("TVCLEAN_ADB", raising=False)
    assert config.default_device() == "192.168.1.253:5555"
    assert config.default_adb_path().endswith("Library/Android/sdk/platform-tools/adb")
