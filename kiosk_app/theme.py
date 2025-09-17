from __future__ import annotations

from typing import Dict

from PySide6.QtGui import QColor

# ---------------------- Светлая тема ----------------------
THEME_DEFAULT: Dict[str, object] = {
    "bg": "#f5f7fb",  # общий фон
    "surface": "#ffffff",  # карточки/кнопки
    "header_bg": "#ffffff",
    "footer_bg": "#ffffff",
    "border": "rgba(0,0,0,0.08)",
    "text": "#0f1419",
    "muted": "rgba(15,20,25,0.65)",
    "primary": "#2563eb",  # синий
    "radius": 14,
    "gap": 16,
    "gap_v": 2,
    "tile_min_w": 320,
    "tile_h": 80,
}


def merge_theme(api_theme: dict | None) -> Dict[str, object]:
    """Merge API-provided theme overrides with the defaults."""
    if not api_theme:
        return THEME_DEFAULT.copy()
    merged = THEME_DEFAULT.copy()
    for key in ("bg", "text", "primary"):
        if api_theme.get(key):
            merged[key] = api_theme[key]
    return merged


def darker(hex_color: str, factor: float = 0.9) -> str:
    """Return the same color slightly darkened by ``factor``."""
    color = QColor(hex_color)
    red = max(0, min(255, int(color.red() * factor)))
    green = max(0, min(255, int(color.green() * factor)))
    blue = max(0, min(255, int(color.blue() * factor)))
    return QColor(red, green, blue).name()
