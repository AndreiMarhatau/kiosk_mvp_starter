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
    "bg_image_path": None,
    "bg_image_local": None,
}


def merge_theme(api_theme: dict | None) -> Dict[str, object]:
    """Merge API-provided theme overrides with the defaults."""
    merged = THEME_DEFAULT.copy()
    if not api_theme:
        return merged

    for key in ("bg", "text", "primary"):
        value = api_theme.get(key)
        if value:
            merged[key] = value

    merged["bg_image_path"] = api_theme.get("bg_image_path") or None
    merged["bg_image_local"] = None
    return merged


def darker(hex_color: str, factor: float = 0.9) -> str:
    """Return the same color slightly darkened by ``factor``."""
    color = QColor(hex_color)
    red = max(0, min(255, int(color.red() * factor)))
    green = max(0, min(255, int(color.green() * factor)))
    blue = max(0, min(255, int(color.blue() * factor)))
    return QColor(red, green, blue).name()


def build_background_qss(theme: Dict[str, object], *, include_image: bool = True) -> str:
    """Compose a background stylesheet string for widgets based on the theme."""

    color = theme.get("bg") or "#f5f7fb"
    parts = [f"background-color: {color};"]
    if include_image:
        path = (theme.get("bg_image_local") or theme.get("bg_image_path") or "")
        if path:
            url = str(path).replace("\\", "/")
            parts.append(
                "background-image: url({}); background-repeat: no-repeat; "
                "background-position: center center; background-size: cover;".format(url)
            )
        else:
            parts.append("background-image: none;")
    else:
        parts.append("background-image: none;")
    return " ".join(parts)
