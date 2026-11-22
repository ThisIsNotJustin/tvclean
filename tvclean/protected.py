"""Packages tvclean must never disable or uninstall."""

PROTECTED_EXACT: frozenset[str] = frozenset({
    "android",
    "com.amazon.tv.launcher",
    "com.amazon.tv.ime",
    "com.amazon.tv.oobe",
    "com.amazon.tv.ooberesource",
    "com.amazon.tv.devicecontrol",
    "com.amazon.tv.devicecontrolsettings",
    "com.amazon.tv.quicksettings",
    "com.amazon.tv.quicksettings.ui",
    "com.amazon.connectivitycontroller",
    "com.amazon.wifilocker",
    "com.amazon.autopairservice",
    "com.amazon.fireinputdevices",
    "com.amazon.device.bluetoothkeymaplib",
    "com.amazon.device.bluetoothpa",
    "com.amazon.android.settings",
    "com.amazon.dummy.settings",
    "com.amazon.hedwig",
    "com.amazon.franktvinput",
    "com.amazon.firebat",
    "com.amazon.ftve.audioprovider",
    "com.amazon.kindleautomatictimezone",
    "com.android.systemui",
    "com.android.bluetooth",
    "com.android.packageinstaller",
    "com.android.permissioncontroller",
    "com.android.certinstaller",
    "com.android.shell",
})

PROTECTED_PREFIXES: tuple[str, ...] = (
    "com.mediatek.",
    "com.amazon.mediatek.",
    "com.amazon.tv.settings",
    "com.amazon.tv.inputpreference",
    "com.amazon.tv.settingsprovider",
    "com.android.networkstack",
    "com.android.wifi",
    "com.android.providers.",
    "com.android.inputmethod",
)


def is_protected(pkg: str) -> bool:
    return pkg in PROTECTED_EXACT or pkg.startswith(PROTECTED_PREFIXES)
