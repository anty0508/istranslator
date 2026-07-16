import ctypes
import time
from ctypes import wintypes

from .logging_setup import log

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
LLKHF_INJECTED = 0x10

VK_CTRLS = {0x11, 0xA2, 0xA3}  # CONTROL, LCONTROL, RCONTROL

wintypes.ULONG_PTR = wintypes.WPARAM
LRESULT = ctypes.c_ssize_t


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.ULONG_PTR),
    ]


HOOKPROC = ctypes.CFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32.SetWindowsHookExW.restype = wintypes.HHOOK
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.CallNextHookEx.restype = LRESULT
user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]


class DoubleTapCtrl:
    def __init__(self, callback, interval=0.4, max_press=0.5):
        self.callback = callback
        self.interval = interval
        self.max_press = max_press
        self._hook = None
        self._proc = HOOKPROC(self._on_key)  # keep alive or Windows crashes
        self._ctrl_down = False
        self._press_start = 0.0
        self._other_since = False
        self._last_tap = 0.0

    def install(self):
        hmod = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, hmod, 0)
        if not self._hook:
            raise OSError(f"SetWindowsHookEx failed (error {ctypes.get_last_error()})")

    def uninstall(self):
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None

    def _fire(self):
        try:
            self.callback()
        except Exception:
            log.exception("double-tap callback failed")

    def _process(self, vk, is_down, injected, now=None):
        if injected:
            return
        if now is None:
            now = time.monotonic()
        is_ctrl = vk in VK_CTRLS

        if is_down:
            if is_ctrl:
                if not self._ctrl_down:
                    self._ctrl_down = True
                    self._press_start = now
                    self._other_since = False
            else:
                self._other_since = True
                self._last_tap = 0.0
        else:
            if is_ctrl and self._ctrl_down:
                self._ctrl_down = False
                clean = (not self._other_since) and (now - self._press_start <= self.max_press)
                if clean:
                    if self._last_tap and (now - self._last_tap <= self.interval):
                        self._last_tap = 0.0
                        self._fire()
                    else:
                        self._last_tap = now
                else:
                    self._last_tap = 0.0

    def _on_key(self, nCode, wParam, lParam):
        try:
            if nCode == 0:
                kb = ctypes.cast(
                    ctypes.c_void_p(lParam), ctypes.POINTER(KBDLLHOOKSTRUCT)
                ).contents
                is_down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
                is_up = wParam in (WM_KEYUP, WM_SYSKEYUP)
                if is_down or is_up:
                    self._process(kb.vkCode, is_down, bool(kb.flags & LLKHF_INJECTED))
        except Exception:
            log.exception("double-tap hook error")
        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)
