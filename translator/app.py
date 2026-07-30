import queue
import threading
import time

from PyQt6.QtCore import QObject, pyqtSignal

from .config import Config
from .logging_setup import log
from .openai_client import TranslationError, translate, warmup
from .overlay import OverlayTooltip
from .selection import get_selected_text, replace_selection
from .win_dtap import DoubleTapCtrl
from .win_hotkeys import NativeHotkeyManager

DOUBLE_CTRL_ALIASES = {"double-ctrl", "doublectrl", "double ctrl", "ctrl-ctrl", "2ctrl"}


def _is_double_ctrl(value):
    return value.strip().lower() in DOUBLE_CTRL_ALIASES


class Bridge(QObject):
    overlay_begin = pyqtSignal()
    overlay_update = pyqtSignal(str)


class TranslatorApp:
    def __init__(self, app):
        self.app = app
        self.config = Config.load()
        self._queue = queue.Queue(maxsize=1)
        self._last_dispatch = 0.0
        self._worker = threading.Thread(
            target=self._worker_loop, daemon=True, name="istranslater-worker"
        )
        self._worker.start()

        self.bridge = Bridge()
        self.bridge.overlay_begin.connect(self._on_overlay_begin)
        self.bridge.overlay_update.connect(self._on_overlay_update)

        self.overlay = OverlayTooltip(self.config["overlay_timeout_ms"])

        self.hotkeys = NativeHotkeyManager(self.app)
        self._dtap = None
        self._register_hotkeys()

        threading.Thread(target=warmup, args=(self.config,), daemon=True).start()

        if not self.config.effective("api_key").strip():
            log.warning("no API key configured (set OPENAI_API_KEY in .env)")

    def _register_hotkeys(self):
        self.hotkeys.clear()
        if self._dtap is not None:
            self._dtap.uninstall()
            self._dtap = None

        translate_cb = lambda: self._dispatch("translate", self._flow_translate)
        try:
            if _is_double_ctrl(self.config["hotkey_translate"]):
                self._dtap = DoubleTapCtrl(translate_cb)
                self._dtap.install()
            else:
                self.hotkeys.register(self.config["hotkey_translate"], translate_cb)

            self.hotkeys.register(
                self.config["hotkey_replace"],
                lambda: self._dispatch("replace", self._flow_replace),
            )
            log.info(
                "hotkeys registered: translate=%r replace=%r",
                self.config["hotkey_translate"],
                self.config["hotkey_replace"],
            )
        except Exception as exc:
            log.exception("hotkey registration failed")

    def _dispatch(self, name, flow):
        now = time.monotonic()
        if now - self._last_dispatch < 0.4:
            return
        self._last_dispatch = now
        log.info("hotkey fired: %s", name)
        try:
            self._queue.put_nowait((name, flow))
        except queue.Full:
            log.info("dropped %s: worker busy", name)

    def _worker_loop(self):
        while True:
            name, flow = self._queue.get()
            try:
                flow()
            except Exception:
                log.exception("flow crashed")

    def _flow_translate(self):
        text, _ = get_selected_text()
        log.info("captured selection: %d chars", len(text))
        if not text.strip():
            log.info("no text selected; skipping")
            return
        self.bridge.overlay_begin.emit()
        try:
            result = translate(text, self.config["lang1"], self.config)
        except TranslationError as exc:
            log.error("translation error: %s", exc)
            return
        log.info("translated -> %d chars, showing overlay", len(result))
        self.bridge.overlay_update.emit(result)

    def _flow_replace(self):
        text, previous = get_selected_text()
        log.info("captured selection: %d chars", len(text))
        if not text.strip():
            log.info("no text selected; skipping")
            return
        try:
            result = translate(text, self.config["lang2"], self.config)
        except TranslationError as exc:
            log.error("translation error: %s", exc)
            return
        log.info("translated -> %d chars, pasting", len(result))
        replace_selection(
            result,
            previous_clipboard=previous,
            restore=self.config["restore_clipboard"],
        )

    def _on_overlay_begin(self):
        try:
            self.overlay.begin()
        except Exception:
            log.exception("overlay begin failed")

    def _on_overlay_update(self, text):
        try:
            self.overlay.update_text(text)
        except Exception:
            log.exception("overlay update failed")
