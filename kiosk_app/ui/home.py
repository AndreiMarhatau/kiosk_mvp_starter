from __future__ import annotations

from typing import Callable, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .styles import add_shadow, button_stylesheet


class KioskTile(QPushButton):
    def __init__(
        self,
        title: str,
        slug: str,
        theme: dict,
        *,
        bg_color: str | None = None,
        on_click: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self.slug = slug
        background = bg_color or theme["primary"]
        self.setStyleSheet(button_stylesheet(background, pad_v=10))
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(theme["tile_h"])

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(0)

        label = QLabel(title)
        label.setStyleSheet("font-size:20px; font-weight:700; background: transparent; color: #ffffff;")
        layout.addStretch(1)
        layout.addWidget(label, 0, Qt.AlignCenter)
        layout.addStretch(1)
        add_shadow(self, blur=16, y=3)
        if on_click:
            self.clicked.connect(lambda: on_click(self.slug))


class DropList(QWidget):
    def __init__(self, theme: dict, items: List[dict], on_pick: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        for item in items:
            btn = QPushButton(item.get("title", ""))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                "background:#ffffff; border:1px solid rgba(0,0,0,0.08);"
                "border-radius:10px; padding:8px 14px; text-align:left;"
            )
            btn.clicked.connect(lambda _, slug=item.get("target_slug", ""): on_pick(slug))
            layout.addWidget(btn)


class GroupTile(QPushButton):
    def __init__(
        self,
        title: str,
        items: List[dict],
        theme: dict,
        *,
        bg_color: str | None = None,
        text_color: str | None = None,
        on_pick: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        background = bg_color or theme["primary"]
        fg = text_color or "#ffffff"
        self.setStyleSheet(button_stylesheet(background, fg=fg, pad_v=10))
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(theme["tile_h"])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size:20px; font-weight:700; background: transparent;")
        layout.addWidget(title_lbl, 0, Qt.AlignCenter)

        drop = DropList(theme, items, on_pick or (lambda slug: None), self)
        drop.setStyleSheet("background: transparent;")
        layout.addWidget(drop)
        add_shadow(self, blur=16, y=3)


class HomePage(QWidget):
    def __init__(self, theme: dict, router: Callable[[str], None]):
        super().__init__()
        self.theme = theme
        self.router = router
        self.buttons_data: List[dict] = []
        self.setStyleSheet(f"background:{theme['bg']}; color:{theme['text']};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(theme["gap"])

        self.wrap = QWidget()
        self.wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer.addWidget(self.wrap, 1)
        self.grid = QGridLayout(self.wrap)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(theme["gap"])
        self.grid.setVerticalSpacing(theme.get("gap_v", theme["gap"]))

    def build(self, top_nodes: List[dict]) -> None:
        self.buttons_data = top_nodes
        self._relayout()

    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        try:
            while self.grid.count():
                item = self.grid.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.hide()
                    widget.setParent(None)
                    widget.deleteLater()
        except Exception:
            for i in reversed(range(self.grid.count())):
                grid_item = self.grid.itemAt(i)
                widget = grid_item.widget() if grid_item else None
                if widget is not None:
                    widget.hide()
                    widget.setParent(None)
        if not self.buttons_data:
            return

        width = max(300, self.width() - 48)
        tile_width = self.theme["tile_min_w"]
        gap = self.theme["gap"]
        cols = max(1, min(4, (width + gap) // (tile_width + gap)))

        flat = sorted(self.buttons_data, key=lambda x: (x.get("order_index") or 0))
        for idx, node in enumerate(flat):
            row, col = divmod(idx, cols)
            if node.get("kind") == "group":
                tile = GroupTile(
                    title=node.get("title", "Группа"),
                    items=node.get("items", []),
                    theme=self.theme,
                    bg_color=node.get("bg_color"),
                    text_color=node.get("text_color"),
                    on_pick=lambda slug, r=self.router: r(slug),
                )
            else:
                tile = KioskTile(
                    title=node.get("title", ""),
                    slug=node.get("target_slug", ""),
                    theme=self.theme,
                    bg_color=node.get("bg_color"),
                    on_click=lambda slug, r=self.router: r(slug),
                )
            self.grid.addWidget(tile, row, col, Qt.AlignTop)

        try:
            rows = (len(flat) + cols - 1) // cols
            for i in range(max(0, rows)):
                try:
                    self.grid.setRowStretch(i, 0)
                except Exception:
                    pass
            try:
                self.grid.setRowStretch(rows, 1)
            except Exception:
                pass
        except Exception:
            pass
