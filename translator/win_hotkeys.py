import ctypes
from ctypes import wintypes

from PyQt6.QtCore import QAbstractNativeEventFilter

from .logging_setup import log

user32 = ctypes.WinDLL("user32", use_last_error=True)

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
user32.VkKeyScanW.restype = ctypes.c_short

WM_HOTKEY = 0x0312

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

MODIFIERS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "windows": MOD_WIN,
    "super": MOD_WIN,
    "cmd": MOD_WIN,
}

NAMED_VK = {
    "space": 0x20,
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "esc": 0x1B,
    "escape": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "del": 0x2E,
    "insert": 0x2D,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
}
for _i in range(1, 13):
    NAMED_VK[f"f{_i}"] = 0x6F + _i


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class HotkeyParseError(Exception):
    pass


def parse_hotkey(text):
    parts = [p.strip().lower() for p in text.split("+") if p.strip()]
    if not parts:
        raise HotkeyParseError(f"empty hotkey: {text!r}")

    modifiers = 0
    key = None
    for part in parts:
        if part in MODIFIERS:
            modifiers |= MODIFIERS[part]
        else:
            key = part

    if key is None:
        raise HotkeyParseError(f"no non-modifier key in {text!r}")

    if key in NAMED_VK:
        vk = NAMED_VK[key]
    elif len(key) == 1:
        res = user32.VkKeyScanW(key)
        if res == -1:
            raise HotkeyParseError(f"cannot map key {key!r}")
        vk = res & 0xFF
    else:
        raise HotkeyParseError(f"unknown key name {key!r}")

    return modifiers | MOD_NOREPEAT, vk


class NativeHotkeyManager(QAbstractNativeEventFilter):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._callbacks = {}
        self._next_id = 1
        app.installNativeEventFilter(self)

    def register(self, hotkey, callback):
        modifiers, vk = parse_hotkey(hotkey)
        hotkey_id = self._next_id
        self._next_id += 1

        if not user32.RegisterHotKey(None, hotkey_id, modifiers, vk):
            err = ctypes.get_last_error()
            raise OSError(
                f"RegisterHotKey failed for {hotkey!r} (error {err}); "
                "another app may already own this combo."
            )

        self._callbacks[hotkey_id] = callback

    def clear(self):
        for hotkey_id in list(self._callbacks):
            user32.UnregisterHotKey(None, hotkey_id)
        self._callbacks.clear()

    def nativeEventFilter(self, eventType, message):
        try:
            addr = int(message) if message else 0
            if addr and bytes(eventType) == b"windows_generic_MSG":
                msg = MSG.from_address(addr)
                if msg.message == WM_HOTKEY:
                    callback = self._callbacks.get(msg.wParam)
                    if callback:
                        callback()
        except Exception:
            log.exception("native event filter error")
        return False, 0
