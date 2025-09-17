from __future__ import annotations

from typing import Callable, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
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
    def __init__(
        self,
        theme: dict,
        items: List[dict],
        on_pick: Callable[[str], None] | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.theme = theme
        self.items = items or []
        self.on_pick = on_pick

        try:
            self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        except Exception:
            self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        try:
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
        except Exception:
            pass
        self.setAutoFillBackground(False)

        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.setSpacing(0)
        self.setStyleSheet("background: transparent;")

        for item in self.items:
            title = item.get("title", "")
            slug = item.get("target_slug", "")
            bg = item.get("bg_color") or theme["primary"]
            fg = item.get("text_color") or "#ffffff"

            btn = QPushButton(title)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                button_stylesheet(bg, fg=fg, radius=10, pad_v=14, pad_h=16, fs=18)
            )
            btn.setMinimumWidth(260)
            try:
                btn.setMinimumHeight(max(44, theme["tile_h"] - 48))
            except Exception:
                btn.setMinimumHeight(44)

            if self.on_pick:
                btn.clicked.connect(lambda _, slug=slug: self._select(slug))

            wrap.addWidget(btn)

    def _select(self, slug: str) -> None:
        self.hide()
        if self.on_pick:
            self.on_pick(slug)


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
        self.theme = theme
        self.items = items or []
        self.on_pick = on_pick

        background = bg_color or theme["primary"]
        fg = text_color or "#ffffff"
        self.setStyleSheet(button_stylesheet(background, fg=fg, pad_v=10))
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(theme["tile_h"])

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 6, 14, 6)
        row.setSpacing(0)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"font-size:20px; font-weight:700; background: transparent; color: {fg};"
        )
        row.addStretch(1)
        row.addWidget(title_lbl, 0, Qt.AlignCenter)
        row.addStretch(1)

        add_shadow(self, blur=16, y=3)
        self.clicked.connect(self._show_list)

    def _show_list(self) -> None:
        popup = DropList(self.theme, self.items, self.on_pick, parent=self)
        try:
            popup.setFixedWidth(max(self.width(), 260))
        except Exception:
            pass
        popup.adjustSize()

        pos = self.mapToGlobal(self.rect().bottomLeft())
        x = pos.x()
        y = pos.y() + 6

        screen_geom = None
        try:
            window = self.window()
            if hasattr(window, "screen") and window.screen():
                screen_geom = window.screen().availableGeometry()
        except Exception:
            screen_geom = None
        if screen_geom is None:
            primary = QGuiApplication.primaryScreen()
            if primary is not None:
                screen_geom = primary.availableGeometry()

        if screen_geom is not None:
            w = popup.width()
            h = popup.sizeHint().height()
            if x + w > screen_geom.right() - 8:
                x = max(8, screen_geom.right() - 8 - w)
            x = max(8, x)
            if y + h > screen_geom.bottom() - 8:
                y = max(8, screen_geom.bottom() - 8 - h)

        popup.move(x, y)
        popup.show()


class HomePage(QWidget):
    def __init__(self, theme: dict, router: Callable[[str], None]):
        super().__init__()
        self.theme = theme
        self.router = router
        self.buttons_data: List[dict] = []
        self.setStyleSheet(f"background: transparent; color:{theme['text']};")

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
