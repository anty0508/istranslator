import logging
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_PATH = Path.home() / ".istranslater" / "istranslater.log"
CRASH_PATH = Path.home() / ".istranslater" / "crash.log"


def setup_logging():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("istranslater")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(
        LOG_PATH, maxBytes=512 * 1024, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(message)s")
    )
    logger.addHandler(handler)

    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter("%(levelname)-7s %(message)s"))
    logger.addHandler(stream)

    return logger


log = setup_logging()

_crash_installed = False


def install_crash_handlers():
    global _crash_installed
    if _crash_installed:
        return
    _crash_installed = True

    try:
        import faulthandler

        CRASH_PATH.parent.mkdir(parents=True, exist_ok=True)
        fh = open(CRASH_PATH, "a", encoding="utf-8")
        faulthandler.enable(file=fh)
    except Exception:
        pass

    def _excepthook(exc_type, exc, tb):
        log.error("UNCAUGHT exception", exc_info=(exc_type, exc, tb))

    def _thread_excepthook(args):
        log.error(
            "UNCAUGHT thread exception in %s",
            getattr(args.thread, "name", "?"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _excepthook
    threading.excepthook = _thread_excepthook

    try:
        from PyQt6.QtCore import qInstallMessageHandler, QtMsgType

        def _qt_handler(mode, context, message):
            if "Unable to set geometry" in message:
                return
            if mode in (QtMsgType.QtFatalMsg, QtMsgType.QtCriticalMsg):
                log.error("Qt: %s", message)
            else:
                log.info("Qt: %s", message)

        qInstallMessageHandler(_qt_handler)
    except Exception:
        pass

