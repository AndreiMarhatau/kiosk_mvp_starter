from __future__ import annotations

from typing import List

from tests.qt_stubs import install_qt_stubs

install_qt_stubs()

from PySide6.QtCore import QUrl  # noqa: E402
from PySide6.QtGui import QPixmap  # noqa: E402
from PySide6.QtMultimedia import QMediaPlayer  # noqa: E402
from PySide6.QtPdf import QPdfDocument  # noqa: E402

from kiosk_app.ui.page import PageView  # noqa: E402


class DummyMediaClient:
    def __init__(self) -> None:
        self.pdf_path = "/tmp/fake.pdf"
        self.video_path = "/tmp/fake.mp4"

    def load_pixmap(self, _path: str) -> QPixmap:
        return QPixmap()

    def ensure_pdf(self, _path: str) -> str:
        return self.pdf_path

    def video_url(self, _path: str) -> QUrl:
        return QUrl.fromLocalFile(self.video_path)

    def ensure_media(self, *_args, **_kwargs):  # pragma: no cover - not used here
        return self.video_path


class DummyRouter:
    def __init__(self) -> None:
        self.history: List[str] = []

    def __call__(self, slug: str) -> None:
        self.history.append(slug)


THEME = {
    "bg": "#ffffff",
    "text": "#000000",
    "gap": 10,
    "tile_h": 80,
    "primary": "#123456",
}


def _reset_multimedia_state() -> None:
    QMediaPlayer.instances.clear()
    QPdfDocument.instances.clear()


def test_render_blocks_disposes_previous_media() -> None:
    _reset_multimedia_state()
    media = DummyMediaClient()
    page = PageView(THEME, DummyRouter(), media)

    blocks = [
        {"kind": "pdf", "content": {"path": "doc.pdf"}},
        {"kind": "video", "content": {"path": "video.mp4"}},
    ]

    page.render_blocks(blocks)
    assert len(QMediaPlayer.instances) == 1
    player = QMediaPlayer.instances[0]
    assert len(QPdfDocument.instances) == 1
    document = QPdfDocument.instances[0]
    assert player.play_called >= 1
    assert document.loaded_path == media.pdf_path

    page.render_blocks([])

    assert player.stop_called >= 1
    assert player.deleted is True
    assert document.closed is True
    assert document.deleted is True
    assert not page._blocks
    assert page.body.count() == 0


def test_render_blocks_recreates_media_on_second_render() -> None:
    _reset_multimedia_state()
    media = DummyMediaClient()
    page = PageView(THEME, DummyRouter(), media)

    blocks = [
        {"kind": "video", "content": {"path": "video.mp4"}},
    ]

    page.render_blocks(blocks)
    first_player = QMediaPlayer.instances[0]
    assert first_player.play_called >= 1

    page.render_blocks(blocks)
    assert len(QMediaPlayer.instances) == 2
    second_player = QMediaPlayer.instances[1]
    assert second_player is not first_player
    assert first_player.stop_called >= 1
    assert first_player.deleted is True
    assert second_player.play_called >= 1


def test_video_block_binds_player_to_widget() -> None:
    _reset_multimedia_state()
    media = DummyMediaClient()
    page = PageView(THEME, DummyRouter(), media)

    page.render_blocks([
        {"kind": "video", "content": {"path": "video.mp4"}},
    ])

    assert len(QMediaPlayer.instances) == 1
    player = QMediaPlayer.instances[0]
    assert player.play_called >= 1
    assert player.video_output is not None
    if hasattr(player.video_output, "widget"):
        assert player.video_output.widget is not None


def test_render_blocks_resets_scroll_position() -> None:
    _reset_multimedia_state()
    media = DummyMediaClient()
    page = PageView(THEME, DummyRouter(), media)

    page.scroll.verticalScrollBar().setValue(350)

    page.render_blocks([
        {"kind": "text", "content": {"html": "<p>Hello</p>"}},
    ])

    assert page.scroll.verticalScrollBar().value() == 0
    assert page.scroll.horizontalScrollBar().value() == 0
