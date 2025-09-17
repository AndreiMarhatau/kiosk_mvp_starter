from __future__ import annotations

from typing import Any, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from ...backend.media import MediaClient
from .base import BlockItem, make_placeholder


def create_image_block(content: Dict[str, Any], media: MediaClient) -> BlockItem:
    label = QLabel()
    label.setStyleSheet("background: transparent;")
    path = content.get("path", "")
    pixmap = media.load_pixmap(path)
    if pixmap and not pixmap.isNull():
        try:
            scaled = pixmap.scaledToWidth(1100, Qt.SmoothTransformation)
            label.setPixmap(scaled)
        except Exception:
            label.setPixmap(pixmap)
    else:
        label = make_placeholder(
            title="Не удалось загрузить изображение",
            subtitle=path,
        )
    return BlockItem(widget=label)


__all__ = ["create_image_block"]
