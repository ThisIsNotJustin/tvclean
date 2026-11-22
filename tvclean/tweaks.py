"""Settings tweaks: animation scales and ad-tracking/usage toggles, applied before the first batch."""
from tvclean.adb import Adb
from tvclean.state import read_setting, setting_reads_back

# "namespace:key" -> value. Keys were confirmed on the TV with `settings list` (read-only):
#   limit_ad_tracking, amz_limit_ad_tracking, non_amz_limit_ad_tracking: 1 = ad tracking limited.
#   USAGE_METRICS_UPLOAD_ENABLED: 0 = usage metrics not uploaded.
TWEAKS: dict[str, str] = {
    "global:window_animation_scale": "0.5",
    "global:transition_animation_scale": "0.5",
    "global:animator_duration_scale": "0.5",
    "secure:limit_ad_tracking": "1",
    "secure:amz_limit_ad_tracking": "1",
    "secure:non_amz_limit_ad_tracking": "1",
    "secure:USAGE_METRICS_UPLOAD_ENABLED": "0",
}


def apply_tweaks(adb: Adb) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """Set each tweak not already at its target, then read it back.

    Returns (changed, failed): changed maps key -> (old, new) for keys that read back as new;
    failed lists keys whose write did not read back as the target.
    """
    changed: dict[str, tuple[str, str]] = {}
    failed: list[str] = []
    for key, new in TWEAKS.items():
        old = read_setting(adb, key)
        if old == new:
            continue
        namespace, _, name = key.partition(":")
        adb.shell(f"settings put {namespace} {name} {new}")
        if setting_reads_back(adb, key, new):
            changed[key] = (old, new)
        else:
            failed.append(key)
    return changed, failed
