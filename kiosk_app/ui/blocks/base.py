from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget


@dataclass
class BlockItem:
    widget: QWidget
    cleanup: Optional[Callable[[], None]] = None

    def dispose(self) -> None:
        if self.cleanup:
            try:
                self.cleanup()
            except Exception:
                pass
            self.cleanup = None
        try:
            self.widget.setParent(None)
        except Exception:
            pass
        try:
            self.widget.deleteLater()
        except Exception:
            pass


__all__ = ["BlockItem"]


def make_placeholder(title: str, subtitle: str = "") -> QLabel:
    label = QLabel(f"{title}\n{subtitle}".strip())
    label.setAlignment(Qt.AlignCenter)
    label.setMinimumHeight(180)
    label.setStyleSheet(
        "border:1px dashed rgba(0,0,0,0.25); border-radius:10px; font-size:14px; color:#666;"
    )
    return label


__all__.append("make_placeholder")
