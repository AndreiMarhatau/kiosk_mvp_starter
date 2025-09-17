from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QFrame,
    QPushButton,
)

from ..backend.media import MediaClient
from .styles import add_shadow


class PageView(QWidget):
    def __init__(self, theme: dict, router, media: MediaClient) -> None:
        super().__init__()
        self.theme = theme
        self.router = router
        self.media = media
        self.setStyleSheet(f"background:{theme['bg']}; color:{theme['text']};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(theme["gap"])
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        try:
            self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        except Exception:
            pass
        outer.addWidget(self.scroll, 1)

        self.page_wrap = QWidget()
        self.scroll.setWidget(self.page_wrap)
        self.body = QVBoxLayout(self.page_wrap)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(theme["gap"])
        self._media_refs: List[tuple] = []

        self.home_btn = QPushButton("На главную")
        self.home_btn.setCursor(Qt.PointingHandCursor)
        self.home_btn.setFixedHeight(48)
        self.home_btn.setStyleSheet(
            "background: #e5e7eb; color:#111; border:0; border-radius:10px;"
            "font-weight:600; font-size:16px; padding:10px 14px;"
        )
        add_shadow(self.home_btn, blur=16, y=6, color="rgba(0,0,0,0.10)")
        self.home_btn.clicked.connect(lambda: self.router("home"))
        outer.addSpacing(8)
        outer.addWidget(self.home_btn, 0, Qt.AlignRight)

    def render_blocks(self, blocks: List[dict]) -> None:
        def clear(layout: QVBoxLayout) -> None:
            for i in reversed(range(layout.count())):
                widget = layout.itemAt(i).widget()
                if widget:
                    widget.setParent(None)

        try:
            for player, audio, video_widget in self._media_refs:
                try:
                    player.stop()
                except Exception:
                    pass
            self._media_refs.clear()
        except Exception:
            pass
        clear(self.body)

        for block in blocks:
            kind = block.get("kind")
            content = block.get("content", {})
            if kind == "text":
                label = QLabel(content.get("html", ""))
                label.setTextFormat(Qt.RichText)
                label.setWordWrap(True)
                label.setStyleSheet("font-size:18px; line-height:1.55; background: transparent;")
                self.body.addWidget(label)
            elif kind == "image":
                img = QLabel()
                img.setStyleSheet("background: transparent;")
                path = content.get("path", "")
                pix = self.media.load_pixmap(path)
                if not pix.isNull():
                    img.setPixmap(pix.scaledToWidth(1100, Qt.SmoothTransformation))
                else:
                    img.setText(f"Не удалось загрузить изображение:\n{path}")
                    img.setAlignment(Qt.AlignCenter)
                    img.setMinimumHeight(180)
                    img.setStyleSheet(
                        "border:1px dashed rgba(0,0,0,0.25); border-radius:10px;"
                        "font-size:14px; color:#666;"
                    )
                self.body.addWidget(img)
            elif kind == "pdf":
                try:
                    from PySide6.QtPdfWidgets import QPdfView
                    from PySide6.QtPdf import QPdfDocument

                    view = QPdfView()
                    document = QPdfDocument(view)
                    local_pdf = self.media.ensure_pdf(content.get("path", ""))
                    if local_pdf:
                        document.load(local_pdf)
                        view.setDocument(document)
                        try:
                            view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
                        except Exception:
                            pass
                        view.setMinimumHeight(620)
                        self.body.addWidget(view)
                    else:
                        placeholder = QLabel(f"Не удалось загрузить PDF:\n{content.get('path', '')}")
                        placeholder.setAlignment(Qt.AlignCenter)
                        placeholder.setMinimumHeight(180)
                        placeholder.setStyleSheet(
                            "border:1px dashed rgba(0,0,0,0.25); border-radius:10px;"
                            "font-size:14px; color:#666;"
                        )
                        self.body.addWidget(placeholder)
                except Exception as exc:
                    self.body.addWidget(QLabel(f"PDF просмотрщик недоступен: {exc}"))
            elif kind == "video":
                try:
                    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
                    from PySide6.QtMultimediaWidgets import QVideoWidget

                    video_widget = QVideoWidget()
                    player = QMediaPlayer()
                    audio = QAudioOutput()
                    try:
                        video_widget.setAttribute(Qt.WA_StyledBackground, True)
                        video_widget.setStyleSheet(f"background:{self.theme['bg']};")
                        video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    except Exception:
                        pass
                    try:
                        audio.setVolume(0.5)
                    except Exception:
                        pass
                    url = self.media.video_url(content.get("path", ""))
                    player.setVideoOutput(video_widget)
                    player.setAudioOutput(audio)
                    player.setSource(url)

                    def _video_error(*_):
                        link = QLabel(f"Видео: {content.get('path', '')}")
                        link.setStyleSheet("color:#2563eb; text-decoration:underline; font-size:16px;")
                        link.setCursor(Qt.PointingHandCursor)
                        link.mousePressEvent = lambda e: QDesktopServices.openUrl(url)  # type: ignore[assignment]
                        self.body.addWidget(link)

                    try:
                        if hasattr(player, "errorOccurred"):
                            player.errorOccurred.connect(_video_error)
                        elif hasattr(player, "errorChanged"):
                            player.errorChanged.connect(_video_error)
                    except Exception:
                        pass

                    player.play()
                    video_widget.setMinimumHeight(460)
                    self.body.addWidget(video_widget)
                    try:
                        self._media_refs.append((player, audio, video_widget))
                    except Exception:
                        self._media_refs = [(player, audio, video_widget)]
                except Exception as exc:
                    self.body.addWidget(QLabel(f"Видео недоступно: {exc}"))
