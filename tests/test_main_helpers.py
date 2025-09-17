import sys
from pathlib import Path

from tests.qt_stubs import install_qt_stubs


install_qt_stubs()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from kiosk_app.backend.media import resolve_url_or_path
from kiosk_app.theme import merge_theme, darker
from kiosk_app.ui.styles import button_stylesheet


def test_resolve_url_or_path_for_media():
    path = "/media/sample.png"
    result = resolve_url_or_path(path, "http://localhost:9000")
    assert result == "http://localhost:9000/media/sample.png"


def test_resolve_url_or_path_for_non_media():
    path = "local/file.png"
    result = resolve_url_or_path(path, "http://localhost:9000")
    assert result == path


def test_merge_theme_overrides_selected_fields():
    overrides = {"bg": "#000000", "primary": "#123456", "unused": "#fff"}
    merged = merge_theme(overrides)
    assert merged["bg"] == "#000000"
    assert merged["primary"] == "#123456"
    assert merged["text"] == merge_theme({})["text"]
    assert "unused" not in merged


def test_button_stylesheet_contains_colors_and_padding():
    style = button_stylesheet("#111111", fg="#222222", radius=10, pad_v=5, pad_h=7, fs=12)
    assert "background: #111111;" in style
    assert "color: #222222;" in style
    assert "border-radius: 10px;" in style
    assert "padding: 5px 7px;" in style
    assert "font-size: 12px;" in style


def test_darker_returns_darker_color():
    original = "#808080"
    darker_color = darker(original, factor=0.5)
    assert darker_color != original

    def hex_to_rgb(value: str) -> tuple[int, int, int]:
        value = value.lstrip("#")
        return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))

    orig_rgb = hex_to_rgb(original)
    darker_rgb = hex_to_rgb(darker_color)
    assert all(dc <= oc for dc, oc in zip(darker_rgb, orig_rgb))
