from pathlib import Path

import pytest

from tvclean.catalog import CatalogError, load_catalog, select

DATA = Path(__file__).parent / "data"


def write(tmp_path, body: str) -> Path:
    path = tmp_path / "catalog.toml"
    path.write_text(body)
    return path


ENTRY = '[[package]]\nname = "com.x.thing"\naction = "disable"\nreason = "A valid reason here"\n'


def test_load_catalog_reads_entries_in_file_order():
    es = load_catalog(DATA / "catalog_ok.toml")
    assert [e.package for e in es] == ["com.safe", "com.mod", "com.alexa", "com.airplay"]
    assert es[0].tier == "safe" and es[0].feature is None
    assert es[1].tier == "moderate"
    assert es[2].feature == "alexa" and es[2].tier is None
    assert es[3].feature == "airplay"
    assert all(e.action == "disable" and len(e.reason) >= 15 for e in es)


def test_load_catalog_rejects_entry_with_both_tier_and_feature(tmp_path):
    path = write(tmp_path, ENTRY + 'tier = "safe"\nfeature = "alexa"\n')
    with pytest.raises(CatalogError, match="com.x.thing"):
        load_catalog(path)


def test_load_catalog_rejects_entry_with_neither_tier_nor_feature(tmp_path):
    path = write(tmp_path, ENTRY)
    with pytest.raises(CatalogError, match="com.x.thing"):
        load_catalog(path)


def test_load_catalog_rejects_duplicate_package(tmp_path):
    path = write(tmp_path, ENTRY + 'tier = "safe"\n' + ENTRY + 'tier = "safe"\n')
    with pytest.raises(CatalogError, match="com.x.thing"):
        load_catalog(path)


def test_load_catalog_rejects_unknown_action(tmp_path):
    path = write(tmp_path, ENTRY.replace('"disable"', '"nuke"') + 'tier = "safe"\n')
    with pytest.raises(CatalogError, match="com.x.thing"):
        load_catalog(path)


def test_load_catalog_rejects_unknown_feature(tmp_path):
    path = write(tmp_path, '[[package]]\nname = "com.x.thing"\naction = "disable"\nreason = "A valid reason here"\nfeature = "gizmo"\n')
    with pytest.raises(CatalogError, match="com.x.thing"):
        load_catalog(path)


def test_select_safe_excludes_moderate_and_features():
    es = load_catalog(DATA / "catalog_ok.toml")
    assert [e.package for e in select(es, "safe", set())] == ["com.safe"]


def test_select_moderate_includes_safe_and_features_off():
    es = load_catalog(DATA / "catalog_ok.toml")  # 1 safe, 1 moderate, 1 alexa, 1 airplay
    names = [e.package for e in select(es, "moderate", {"alexa"})]
    assert names == ["com.safe", "com.mod", "com.alexa"]


@pytest.mark.parametrize("name", ["com.x; reboot", "com.x y", "com.x$(id)", "1com.x", "com.x-y"])
def test_load_catalog_rejects_names_that_are_not_package_names(tmp_path, name):
    body = ENTRY.replace("com.x.thing", name) + 'tier = "safe"\n'
    with pytest.raises(CatalogError, match="not a package name"):
        load_catalog(write(tmp_path, body))
