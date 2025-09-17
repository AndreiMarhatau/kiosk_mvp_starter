from __future__ import annotations

from typing import Any, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from .base import BlockItem


def create_text_block(content: Dict[str, Any]) -> BlockItem:
    label = QLabel(content.get("html", ""))
    label.setTextFormat(Qt.RichText)
    label.setWordWrap(True)
    label.setStyleSheet("font-size:18px; line-height:1.55; background: transparent;")
    return BlockItem(widget=label)


__all__ = ["create_text_block"]
