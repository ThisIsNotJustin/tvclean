"""The curated package catalog: load, validate and select entries."""
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
import tomllib

from tvclean.protected import is_protected

ACTIONS = ("disable", "uninstall")
TIERS = ("safe", "moderate")
FEATURES = ("alexa", "airplay", "updates")


class CatalogError(ValueError):
    """The catalog file is malformed or lists a protected package."""


@dataclass(frozen=True)
class Entry:
    package: str
    action: Literal["disable", "uninstall"]
    reason: str
    tier: Literal["safe", "moderate"] | None = None
    feature: Literal["alexa", "airplay", "updates"] | None = None


def _entry(raw: dict) -> Entry:
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise CatalogError(f"entry has no package name: {raw!r}")
    if is_protected(name):
        raise CatalogError(f"{name} is on the protected list and must not be in the catalog")
    action = raw.get("action")
    if action not in ACTIONS:
        raise CatalogError(f"{name}: unknown action {action!r}")
    reason = raw.get("reason")
    if not isinstance(reason, str) or not reason:
        raise CatalogError(f"{name}: missing reason")
    tier = raw.get("tier")
    feature = raw.get("feature")
    if (tier is None) == (feature is None):
        raise CatalogError(f"{name}: must set exactly one of tier or feature")
    if tier is not None and tier not in TIERS:
        raise CatalogError(f"{name}: unknown tier {tier!r}")
    if feature is not None and feature not in FEATURES:
        raise CatalogError(f"{name}: unknown feature {feature!r}")
    return Entry(package=name, action=action, reason=reason, tier=tier, feature=feature)


def load_catalog(path: Path) -> list[Entry]:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    entries: list[Entry] = []
    seen: set[str] = set()
    for raw in data.get("package", []):
        entry = _entry(raw)
        if entry.package in seen:
            raise CatalogError(f"{entry.package} appears more than once in the catalog")
        seen.add(entry.package)
        entries.append(entry)
    return entries


def select(entries: list[Entry], tier: str, features_off: set[str]) -> list[Entry]:
    """Entries to apply at `tier`, plus every entry whose feature is switched off."""
    wanted_tiers = {"safe"} if tier == "safe" else {"safe", "moderate"}
    return [
        e for e in entries
        if e.tier in wanted_tiers or (e.feature is not None and e.feature in features_off)
    ]
