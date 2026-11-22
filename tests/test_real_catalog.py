from pathlib import Path

from tvclean.catalog import load_catalog
from tvclean.protected import is_protected

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "packages.toml"
DEVICE = ROOT / "data" / "device_packages.txt"


def test_real_catalog_loads():
    assert load_catalog(CATALOG)


def test_every_entry_exists_on_this_tv():
    names = set(DEVICE.read_text().split())
    assert [e.package for e in load_catalog(CATALOG) if e.package not in names] == []


def test_no_entry_is_protected():
    assert [e.package for e in load_catalog(CATALOG) if is_protected(e.package)] == []


def test_required_entries():
    by = {e.package: e for e in load_catalog(CATALOG)}
    for p in ("com.instagram.airwave", "com.roku.web.trc", "tv.pluto.android"):
        assert by[p].action == "disable" and by[p].tier == "safe"
    # The brief names com.amazon.airplaydaemon, but that is a process name, not an
    # installed package (pm lists com.apple.airplay.amazon.airplay). See report.
    assert by["com.apple.airplay.amazon.airplay"].feature == "airplay"
    assert by["com.amazon.vizzini"].feature == "alexa"
    for p in ("com.amazon.device.software.ota", "com.amazon.device.software.ota.override", "com.amazon.tv.forcedotaupdater.v2"):
        assert by[p].feature == "updates"


def test_every_entry_has_a_real_reason():
    assert all(len(e.reason) >= 15 for e in load_catalog(CATALOG))


def test_moderate_entries_name_the_risk():
    moderate = [e for e in load_catalog(CATALOG) if e.tier == "moderate"]
    assert moderate
    assert all("may break" in e.reason for e in moderate)


def test_no_forbidden_areas():
    forbidden = ("live", "tuner", "hdmi", "cec", ".ime", "launcher", "settings", "wifi",
                 "venezia", "drm", "widevine", "playready", "parental", "accessib", "bluetooth")
    bad = [e.package for e in load_catalog(CATALOG)
           if any(word in e.package.lower() for word in forbidden)]
    assert bad == []
