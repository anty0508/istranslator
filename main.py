import sys

from PyQt6.QtWidgets import QApplication

from translator.logging_setup import install_crash_handlers
from translator.app import TranslatorApp


def main():
    install_crash_handlers()
    app = QApplication(sys.argv)
    app.setApplicationName("iSTranslater")
    app.setQuitOnLastWindowClosed(False)

    TranslatorApp(app)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
