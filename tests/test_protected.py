from pathlib import Path

import pytest

from tvclean.catalog import CatalogError, load_catalog
from tvclean.protected import is_protected

DATA = Path(__file__).parent / "data"


@pytest.mark.parametrize("pkg", [
    "com.amazon.tv.launcher", "com.mediatek.tis", "com.mediatek.customerpq",
    "com.amazon.tv.settings.v2", "com.amazon.tv.inputpreference.service", "com.android.networkstack.tethering",
    "com.amazon.tv.ime", "com.android.bluetooth", "com.amazon.autopairservice",
])
def test_is_protected(pkg):
    assert is_protected(pkg)


@pytest.mark.parametrize("pkg", ["com.amazon.vizzini", "com.instagram.airwave", "com.amazon.airplaydaemon"])
def test_not_protected(pkg):
    assert not is_protected(pkg)


def test_load_catalog_rejects_protected_package():
    with pytest.raises(CatalogError, match="com.mediatek.tis"):
        load_catalog(DATA / "catalog_protected.toml")
