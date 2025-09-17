from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

if __package__ is None:  # pragma: no cover - script execution support
    package_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(package_dir))
    from kiosk_app.app import App  # type: ignore
else:  # pragma: no cover
    from .app import App


def _configure_qt_logging() -> None:
    try:
        from PySide6.QtCore import qInstallMessageHandler
    except Exception:  # pragma: no cover - Qt install unavailable
        return

    previous_handler = None

    def _qt_msg_handler(mode, context, message):
        nonlocal previous_handler
        if isinstance(message, str) and "AVStream duration -9223372036854775808 is invalid" in message:
            return
        if previous_handler:
            previous_handler(mode, context, message)

    previous_handler = qInstallMessageHandler(_qt_msg_handler)


def main() -> int:
    _configure_qt_logging()
    app = QApplication(sys.argv)
    window = App()
    window.resize(1280, 800)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
