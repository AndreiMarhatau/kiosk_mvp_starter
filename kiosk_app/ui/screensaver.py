from __future__ import annotations

import os
from typing import Callable, Optional

from PySide6.QtCore import QEvent, Qt, QUrl
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..backend.media import MediaClient


class ScreensaverLayer(QWidget):
    """Fullscreen overlay that plays idle media while the kiosk is inactive."""

    _VIDEO_EXTS = {".mp4", ".webm", ".avi", ".mov", ".mkv"}
    _IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
    _GIF_EXTS = {".gif"}

    def __init__(
        self,
        media: MediaClient,
        *,
        on_exit: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.media = media
        self._on_exit = on_exit

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setStyleSheet("background-color:#000000;")
        self.setVisible(False)
        self.setFocusPolicy(Qt.NoFocus)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        self._message = QLabel("Нет медиа", self)
        self._message.setAlignment(Qt.AlignCenter)
        self._message.setStyleSheet("color:#ffffff; font-size:32px; padding:16px;")
        layout.addWidget(self._message, 0, Qt.AlignCenter)

        self._image = QLabel(self)
        self._image.setAlignment(Qt.AlignCenter)
        self._image.setStyleSheet("background:transparent;")
        layout.addWidget(self._image, 0, Qt.AlignCenter)
        self._image.hide()

        self._movie_label = QLabel(self)
        self._movie_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._movie_label, 0, Qt.AlignCenter)
        self._movie_label.hide()

        self._video_container = QWidget(self)
        self._video_layout = QVBoxLayout(self._video_container)
        self._video_layout.setContentsMargins(0, 0, 0, 0)
        self._video_layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._video_container, 0, Qt.AlignCenter)
        self._video_container.hide()

        self._movie: Optional[QMovie] = None
        self._player = None
        self._audio = None
        self._video_widget = None

    def set_exit_callback(self, callback: Callable[[], None] | None) -> None:
        self._on_exit = callback

    # ---------------------- Public API ----------------------
    def hide_media(self) -> None:
        self._cleanup()
        self.hide()

    def show_media(self, path: Optional[str]) -> bool:
        self._cleanup()
        if not path:
            self._message.setText("Нет медиа")
            self._message.show()
            self.show()
            self.raise_()
            return False

        ext = os.path.splitext(path.split("?")[0])[-1].lower()
        success = False
        if ext in self._IMAGE_EXTS:
            success = self._show_image(path)
        elif ext in self._GIF_EXTS:
            success = self._show_gif(path)
        elif ext in self._VIDEO_EXTS:
            success = self._show_video(path)
        else:
            name = os.path.basename(path.split("?")[0]) or path
            self._message.setText(f"Файл: {name}")
            self._message.show()

        self.show()
        self.raise_()
        return success

    # ---------------------- Internals ----------------------
    def _cleanup(self) -> None:
        if self._movie:
            try:
                self._movie.stop()
            except Exception:
                pass
            try:
                self._movie.deleteLater()
            except Exception:
                pass
        self._movie = None
        if self._player:
            try:
                self._player.stop()
            except Exception:
                pass
            try:
                self._player.deleteLater()
            except Exception:
                pass
        self._player = None
        if self._audio:
            try:
                self._audio.deleteLater()
            except Exception:
                pass
        self._audio = None
        if self._video_widget:
            try:
                self._video_widget.deleteLater()
            except Exception:
                pass
        self._video_widget = None
        while self._video_layout.count():
            item = self._video_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None:
                widget.setParent(None)
        self._video_container.hide()
        self._movie_label.hide()
        self._image.hide()
        self._image.clear()
        self._message.hide()
        self._message.setText("Нет медиа")

    def _show_image(self, path: str) -> bool:
        pixmap = self.media.load_pixmap(path)
        if pixmap and not pixmap.isNull():
            width = max(320, int(self.width() * 0.9) or 800)
            height = max(240, int(self.height() * 0.9) or 600)
            scaled = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._image.setPixmap(scaled)
            self._image.show()
            return True
        self._message.setText("Не удалось загрузить изображение")
        self._message.show()
        return False

    def _show_gif(self, path: str) -> bool:
        local_path = self.media.ensure_media(path, limit_bytes=50 * 1024 * 1024)
        if not local_path:
            self._message.setText("Не удалось загрузить GIF")
            self._message.show()
            return False
        movie = QMovie(local_path)
        if not movie.isValid():
            self._message.setText("Не удалось загрузить GIF")
            self._message.show()
            return False
        self._movie = movie
        self._movie_label.setMovie(movie)
        self._movie_label.show()
        movie.start()
        return True

    def _show_video(self, path: str) -> bool:
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
            from PySide6.QtMultimediaWidgets import QVideoWidget
        except Exception:
            self._message.setText("Модуль QtMultimedia недоступен")
            self._message.show()
            return False

        url = self.media.video_url(path)
        video_widget = QVideoWidget(self)
        video_widget.setAttribute(Qt.WA_StyledBackground, True)
        video_widget.setStyleSheet("background-color:#000;")
        video_widget.setMinimumSize(640, 360)
        player = QMediaPlayer(self)
        audio = QAudioOutput(self)
        try:
            audio.setVolume(0.0)
        except Exception:
            pass
        player.setVideoOutput(video_widget)
        player.setAudioOutput(audio)
        player.setSource(url)
        try:
            if hasattr(player, "setLoops"):
                loops = getattr(player, "Loops", None)
                if loops and hasattr(loops, "Infinite"):
                    player.setLoops(loops.Infinite)
                else:
                    player.setLoops(-1)
        except Exception:
            pass

        self._video_widget = video_widget
        self._player = player
        self._audio = audio
        self._video_layout.addWidget(video_widget, 0, Qt.AlignCenter)
        self._video_container.show()
        player.play()
        return True

    # ---------------------- Event handling ----------------------
    def mousePressEvent(self, event):  # type: ignore[override]
        self._trigger_exit()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):  # type: ignore[override]
        self._trigger_exit()
        super().keyPressEvent(event)

    def event(self, event):  # type: ignore[override]
        if event.type() in (QEvent.TouchBegin, QEvent.TouchUpdate, QEvent.TouchEnd):
            self._trigger_exit()
            return True
        return super().event(event)

    def _trigger_exit(self) -> None:
        try:
            self.hide_media()
        except Exception:
            pass
        if callable(self._on_exit):
            try:
                self._on_exit()
            except Exception:
                pass
