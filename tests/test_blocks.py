from __future__ import annotations

from typing import Any, Dict

from tests.qt_stubs import install_qt_stubs

install_qt_stubs()

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QPixmap  # noqa: E402
from PySide6.QtPdf import QPdfDocument  # noqa: E402
from PySide6.QtWidgets import QLabel  # noqa: E402
from PySide6.QtMultimedia import QMediaPlayer  # noqa: E402

from kiosk_app.ui.blocks import (
    BlockItem,
    create_image_block,
    create_pdf_block,
    create_text_block,
    create_video_block,
)


class DummyMedia:
    def __init__(self) -> None:
        self.pdf = "/tmp/test.pdf"
        self.video = "/tmp/test.mp4"
        self.image_called = False

    def load_pixmap(self, _path: str) -> QPixmap:
        self.image_called = True
        return QPixmap()

    def ensure_pdf(self, _path: str) -> str:
        return self.pdf

    def video_url(self, _path: str) -> QUrl:
        return QUrl.fromLocalFile(self.video)

    def ensure_media(self, *_args: Any, **_kwargs: Any) -> str:
        return self.video


THEME: Dict[str, Any] = {
    "bg": "#fff",
    "gap": 12,
}


def _reset_players() -> None:
    QMediaPlayer.instances.clear()


def _reset_pdfs() -> None:
    QPdfDocument.instances.clear()


def test_create_text_block_returns_rich_label() -> None:
    item = create_text_block({"html": "<p>Hello</p>"})
    assert isinstance(item, BlockItem)
    assert isinstance(item.widget, QLabel)
    item.dispose()


def test_create_image_block_uses_media_client() -> None:
    media = DummyMedia()
    item = create_image_block({"path": "image.png"}, media)
    assert media.image_called is True
    assert isinstance(item.widget, QLabel)
    item.dispose()


def test_create_pdf_block_registers_document() -> None:
    _reset_pdfs()
    media = DummyMedia()
    item = create_pdf_block({"path": "doc.pdf"}, media)
    assert len(QPdfDocument.instances) == 1
    doc = QPdfDocument.instances[0]
    assert doc.loaded_path == media.pdf
    item.dispose()
    assert doc.closed is True


def test_create_video_block_binds_output_and_cleans_up() -> None:
    _reset_players()
    media = DummyMedia()
    parent = QLabel()
    item = create_video_block({"path": "video.mp4"}, media, THEME, parent)
    assert len(QMediaPlayer.instances) == 1
    player = QMediaPlayer.instances[0]
    assert player.play_called >= 1
    assert player.video_output is not None
    item.dispose()
    assert player.stop_called >= 1
    assert player.deleted is True
