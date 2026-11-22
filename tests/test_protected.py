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


ADDED_PROTECTED = [
    "com.amazon.tv.livetv", "com.amazon.tv.channelscan", "com.amazon.livedeviceservice",
    "com.amazon.device.blepa", "com.amazon.device.singlebankpa", "com.amazon.tv.keypolicymanager",
    "com.amazon.android.tv.globalkey.overlay.ginza", "com.amazon.tv.arc", "com.amazon.tv.routing",
    "com.amazon.firehomestarter", "com.amazon.venezia", "com.amazon.identity.auth.device.authorization",
    "com.amazon.webview.chromium",
]


@pytest.mark.parametrize("pkg", ADDED_PROTECTED)
def test_added_protected_names(pkg):
    assert is_protected(pkg)


# One package per category from the design spec's protected list (plus Appstore and sign-in).
CATEGORY_PACKAGES = {
    "launcher": "com.amazon.tv.launcher",
    "settings": "com.amazon.android.settings",
    "inputs/HDMI": "com.amazon.tv.arc",
    "picture": "com.mediatek.customerpq",
    "remote/BT pairing": "com.amazon.device.blepa",
    "IME": "com.amazon.tv.ime",
    "Wi-Fi/network": "com.amazon.wifilocker",
    "installer": "com.android.packageinstaller",
    "Live TV": "com.amazon.tv.livetv",
    "Appstore": "com.amazon.venezia",
    "sign-in": "com.amazon.identity.auth.device.authorization",
}


@pytest.mark.parametrize("category", list(CATEGORY_PACKAGES))
def test_each_category_has_a_protected_package(category):
    assert is_protected(CATEGORY_PACKAGES[category])
