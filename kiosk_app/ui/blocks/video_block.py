from __future__ import annotations

from typing import Any, Dict

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from ...backend.media import MediaClient
from .base import BlockItem, make_placeholder


def create_video_block(
    content: Dict[str, Any],
    media: MediaClient,
    theme: Dict[str, Any],
    parent: QWidget,
) -> BlockItem:
    try:
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        from PySide6.QtMultimediaWidgets import QVideoWidget
    except Exception as exc:  # pragma: no cover - QtMultimedia unavailable
        return BlockItem(widget=make_placeholder("Видео недоступно", str(exc)))

    container = QWidget(parent)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(int(theme.get("gap", 12)))

    video_widget = QVideoWidget(container)
    try:
        video_widget.setAttribute(Qt.WA_StyledBackground, True)
        video_widget.setStyleSheet(f"background:{theme.get('bg', '#000')};")
        video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    except Exception:
        pass
    video_widget.setMinimumHeight(460)
    layout.addWidget(video_widget)

    player = QMediaPlayer(parent)
    audio = QAudioOutput(parent)
    try:
        audio.setVolume(0.5)
    except Exception:
        pass

    url = media.video_url(content.get("path", ""))
    _bind_video_output(player, video_widget)
    player.setAudioOutput(audio)
    player.setSource(url)

    fallback_added = {"shown": False}

    def _show_fallback() -> None:
        if fallback_added["shown"]:
            return
        fallback_added["shown"] = True
        link = QLabel(f"Видео: {content.get('path', '')}")
        link.setStyleSheet("color:#2563eb; text-decoration:underline; font-size:16px;")
        link.setAlignment(Qt.AlignCenter)
        link.setCursor(Qt.PointingHandCursor)
        link.mousePressEvent = lambda _evt: QDesktopServices.openUrl(url)  # type: ignore[assignment]
        layout.addWidget(link)

    try:
        if hasattr(player, "errorOccurred"):
            player.errorOccurred.connect(lambda *_: _show_fallback())
        elif hasattr(player, "errorChanged"):
            player.errorChanged.connect(lambda *_: _show_fallback())
    except Exception:
        pass

    try:
        player.play()
        QTimer.singleShot(0, player.play)
    except Exception:
        pass

    container.setMinimumHeight(460)

    def _cleanup() -> None:
        for action in (
            lambda: player.stop(),
            lambda: player.setSource(QUrl()),
            lambda: audio.deleteLater(),
            lambda: player.deleteLater(),
        ):
            try:
                action()
            except Exception:
                pass

    return BlockItem(widget=container, cleanup=_cleanup)


def _bind_video_output(player, video_widget: QWidget) -> None:
    output_bound = False
    try:
        if hasattr(video_widget, "videoSink"):
            sink = video_widget.videoSink()
            if sink is not None:
                player.setVideoOutput(sink)
                output_bound = True
    except Exception:
        output_bound = False
    if not output_bound:
        try:
            if hasattr(video_widget, "setMediaPlayer"):
                video_widget.setMediaPlayer(player)
                output_bound = True
        except Exception:
            output_bound = False
    if not output_bound:
        try:
            player.setVideoOutput(video_widget)
        except Exception:
            pass


__all__ = ["create_video_block"]
