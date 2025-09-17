from __future__ import annotations

from typing import List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget, QFrame, QPushButton

from ..backend.media import MediaClient
from ..theme import build_background_qss
from .styles import add_shadow
from .page_blocks import BlockItem, build_block_widget


class PageView(QWidget):
    def __init__(self, theme: dict, router, media: MediaClient) -> None:
        super().__init__()
        self.theme = theme
        self.router = router
        self.media = media
        self.setStyleSheet(f"{build_background_qss(theme, include_image=False)} color:{theme['text']};")

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
        self._blocks: List[BlockItem] = []

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
        self._dispose_blocks()
        self._clear_layout(self.body)
        self._blocks.clear()

        for block in blocks:
            item = build_block_widget(
                block,
                theme=self.theme,
                media=self.media,
                router=self.router,
                parent=self,
            )
            if not item:
                continue
            self.body.addWidget(item.widget)
            self._blocks.append(item)

        self._reset_scroll()

    def clear(self) -> None:
        self.render_blocks([])

    def _dispose_blocks(self) -> None:
        while self._blocks:
            block = self._blocks.pop()
            try:
                block.dispose()
            except Exception:
                pass

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                try:
                    widget.deleteLater()
                except Exception:
                    widget.setParent(None)
            if child_layout is not None:
                self._clear_layout(child_layout)  # type: ignore[arg-type]

    def _reset_scroll(self) -> None:
        try:
            vbar = getattr(self.scroll, "verticalScrollBar", lambda: None)()
            if vbar is not None and hasattr(vbar, "setValue"):
                vbar.setValue(0)
        except Exception:
            pass
        try:
            hbar = getattr(self.scroll, "horizontalScrollBar", lambda: None)()
            if hbar is not None and hasattr(hbar, "setValue"):
                hbar.setValue(0)
        except Exception:
            pass
        try:
            if hasattr(self.scroll, "ensureVisible"):
                self.scroll.ensureVisible(0, 0)
        except Exception:
            pass
