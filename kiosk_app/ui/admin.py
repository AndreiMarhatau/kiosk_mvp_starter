from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    QWebEngineView = None  # type: ignore


class AdminView(QWidget):
    def __init__(self, theme: dict):
        super().__init__()
        self.theme = theme
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        if QWebEngineView is not None:
            self.view = QWebEngineView(self)
            layout.addWidget(self.view)
        else:
            self.view = None
            label = QLabel("Встроенный браузер недоступен. Откроем во внешнем браузере.")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)

    def load(self, url: str) -> None:
        if self.view is not None:
            try:
                self.view.load(QUrl(url))  # type: ignore[attr-defined]
            except Exception:
                pass
        else:
            try:
                QDesktopServices.openUrl(QUrl(url))
            except Exception:
                pass
