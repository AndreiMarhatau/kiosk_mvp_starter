from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QHBoxLayout, QWidget


class Footer(QWidget):
    def __init__(self, theme: dict, clock_format: str = "%H:%M", qr_text: str = "") -> None:
        super().__init__()
        self.setStyleSheet(
            f"background:{theme['footer_bg']}; color:{theme['muted']};"
            f"border-top:1px solid {theme['border']};"
        )
        self.clock = QLabel()
        self.clock.setStyleSheet("font-size:18px; background: transparent;")
        self.qr = QLabel()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.addWidget(self.clock)
        layout.addStretch()
        layout.addWidget(self.qr)

        self._clock_format = clock_format or "%H:%M"
        self.set_qr(qr_text)
        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(1000)
        self._timer = timer
        self._tick()

    def set_qr(self, text: str) -> None:
        self.qr.clear()
        if not text:
            return
        try:
            import qrcode
            from PIL.ImageQt import ImageQt

            img = qrcode.make(text)
            qim = ImageQt(img)
            pix = QPixmap.fromImage(qim)
            self.qr.setPixmap(
                pix.scaled(QSize(88, 88), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        except Exception:
            pass

    def _tick(self) -> None:
        from datetime import datetime

        self.clock.setText(datetime.now().strftime(self._clock_format))
