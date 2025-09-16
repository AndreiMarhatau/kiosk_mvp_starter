from __future__ import annotations

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect

from ..theme import darker


def button_stylesheet(
    background: str,
    *,
    fg: str = "#ffffff",
    radius: int = 14,
    pad_v: int = 22,
    pad_h: int = 22,
    fs: int = 20,
) -> str:
    """Return a styled QPushButton stylesheet with consistent hover/press states."""
    hover = darker(background, 0.92)
    pressed = darker(background, 0.85)
    return f"""
        QPushButton {{
            background: {background};
            color: {fg};
            border: 0px;
            border-radius: {radius}px;
            padding: {pad_v}px {pad_h}px;
            font-size: {fs}px;
            font-weight: 700;
            text-align: center;
        }}
        QPushButton:hover {{ background: {hover}; }}
        QPushButton:pressed {{ background: {pressed}; }}
        QPushButton:disabled {{
            background: rgba(0,0,0,0.05);
            color: rgba(0,0,0,0.4);
        }}
        QPushButton:focus {{ outline: none; }}
    """


def add_shadow(
    widget: QWidget,
    *,
    blur: int = 22,
    x: int = 0,
    y: int = 8,
    color: str = "rgba(0,0,0,0.12)",
) -> None:
    """Attach a drop shadow effect to *widget* with consistent defaults."""
    effect = QGraphicsDropShadowEffect()
    effect.setBlurRadius(blur)
    effect.setXOffset(x)
    effect.setYOffset(y)
    effect.setColor(QColor(color))
    widget.setGraphicsEffect(effect)
