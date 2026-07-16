import ctypes
import time

import pyperclip

from .logging_setup import log
from .win_input import release_modifiers, send_copy, send_paste

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_user32.GetClipboardSequenceNumber.restype = ctypes.c_uint


def _clipboard_seq():
    return _user32.GetClipboardSequenceNumber()


def _safe_paste_get():
    try:
        return pyperclip.paste()
    except Exception:
        return ""


def _safe_copy_set(value):
    try:
        pyperclip.copy(value)
    except Exception:
        pass


def _wait_seq_change(seq0, timeout):
    deadline = time.time() + timeout
    while _clipboard_seq() == seq0 and time.time() < deadline:
        time.sleep(0.01)
    return _clipboard_seq() != seq0


def get_selected_text(settle=1.0):
    previous = _safe_paste_get()
    seq0 = _clipboard_seq()

    release_modifiers()
    time.sleep(0.05)
    send_copy()

    if not _wait_seq_change(seq0, settle):
        log.info("clipboard sequence unchanged after ctrl+c")
        return "", previous

    return _safe_paste_get(), previous


def replace_selection(new_text, previous_clipboard=None, restore=True):
    _safe_copy_set(new_text)
    time.sleep(0.05)

    release_modifiers()
    time.sleep(0.06)
    send_paste()
    time.sleep(0.15)

    if restore and previous_clipboard is not None:
        _safe_copy_set(previous_clipboard)
