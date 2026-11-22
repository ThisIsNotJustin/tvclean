"""Settings tweaks: animation scales and ad-tracking/usage toggles, applied before the first batch."""
from tvclean.adb import Adb
from tvclean.state import _read_setting

# "namespace:key" -> value. Ad and usage keys were confirmed on the TV with `settings list`:
#   limit_ad_tracking, amz_limit_ad_tracking, non_amz_limit_ad_tracking: 1 = ad tracking limited.
#   USAGE_METRICS_UPLOAD_ENABLED, pact_usage_collection_enabled,
#   usage_metrics_marketing_enabled: 0 = usage data not uploaded or used for marketing.
TWEAKS: dict[str, str] = {
    "global:window_animation_scale": "0.5",
    "global:transition_animation_scale": "0.5",
    "global:animator_duration_scale": "0.5",
    "secure:limit_ad_tracking": "1",
    "secure:amz_limit_ad_tracking": "1",
    "secure:non_amz_limit_ad_tracking": "1",
    "secure:USAGE_METRICS_UPLOAD_ENABLED": "0",
    "secure:pact_usage_collection_enabled": "0",
    "secure:usage_metrics_marketing_enabled": "0",
}


def apply_tweaks(adb: Adb) -> dict[str, tuple[str, str]]:
    """Set each tweak that is not already at its target. Returns key -> (old, new) for changes only."""
    changed: dict[str, tuple[str, str]] = {}
    for key, new in TWEAKS.items():
        old = _read_setting(adb, key)
        if old == new:
            continue
        namespace, _, name = key.partition(":")
        adb.shell(f"settings put {namespace} {name} {new}")
        changed[key] = (old, new)
    return changed
