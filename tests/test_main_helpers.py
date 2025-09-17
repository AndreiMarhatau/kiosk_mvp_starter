import sys
import types
from pathlib import Path


def _install_qt_stubs():
    """Provide minimal PySide6 stubs so helper modules can be imported without Qt."""
    if "PySide6" in sys.modules:
        return

    def _dummy_class(name, **attrs):
        def __init__(self, *args, **kwargs):
            pass

        namespace = {"__init__": __init__, "__module__": name}
        namespace.update(attrs)
        return type(name, (), namespace)

    class _FakeQColor:
        def __init__(self, *args):
            if len(args) == 1 and isinstance(args[0], str):
                value = args[0]
                if value.startswith("#") and len(value) == 7:
                    self._r = int(value[1:3], 16)
                    self._g = int(value[3:5], 16)
                    self._b = int(value[5:7], 16)
                else:
                    self._r = self._g = self._b = 0
            elif len(args) == 3:
                self._r, self._g, self._b = [int(a) for a in args]
            else:
                self._r = self._g = self._b = 0

        def red(self):
            return self._r

        def green(self):
            return self._g

        def blue(self):
            return self._b

        def name(self):
            return f"#{self._r:02x}{self._g:02x}{self._b:02x}"

    qtwidgets = types.ModuleType("PySide6.QtWidgets")
    for cls_name in [
        "QApplication",
        "QWidget",
        "QVBoxLayout",
        "QHBoxLayout",
        "QLabel",
        "QPushButton",
        "QStackedWidget",
        "QGridLayout",
        "QSizePolicy",
        "QFrame",
        "QScrollArea",
        "QSpacerItem",
        "QMenu",
        "QGraphicsDropShadowEffect",
        "QInputDialog",
        "QLineEdit",
        "QDialog",
        "QDialogButtonBox",
        "QCheckBox",
        "QMessageBox",
    ]:
        setattr(qtwidgets, cls_name, _dummy_class(cls_name))
    qtwidgets.QDialogButtonBox.Ok = 1
    qtwidgets.QDialogButtonBox.Cancel = 2
    qtwidgets.QLineEdit.Normal = 0
    qtwidgets.QLineEdit.Password = 1

    def _warning_stub(*args, **kwargs):
        return None

    qtwidgets.QMessageBox.warning = staticmethod(_warning_stub)

    qtcore = types.ModuleType("PySide6.QtCore")
    qtcore.Qt = types.SimpleNamespace(
        AlignVCenter=0,
        AlignCenter=0,
        AlignRight=0,
        AlignTop=0,
        SmoothTransformation=0,
        KeepAspectRatio=0,
        PointingHandCursor=0,
        WA_StyledBackground=0,
        RichText=0,
        ScrollBarAlwaysOff=0,
    )
    qtcore.QTimer = _dummy_class("QTimer")
    qtcore.QSize = _dummy_class("QSize")
    qtcore.QUrl = _dummy_class("QUrl")
    qtcore.QEvent = _dummy_class("QEvent")

    qtgui = types.ModuleType("PySide6.QtGui")
    class _FakeQPixmap:
        def __init__(self, *args, **kwargs):
            pass

        @staticmethod
        def fromImage(image):
            return _FakeQPixmap()

        def scaled(self, *args, **kwargs):
            return self

        def scaledToHeight(self, *args, **kwargs):
            return self

        def scaledToWidth(self, *args, **kwargs):
            return self

        def isNull(self):
            return False

    qtgui.QPixmap = _FakeQPixmap
    qtgui.QColor = _FakeQColor
    qtgui.QFont = _dummy_class("QFont")
    qtgui.QImage = _dummy_class("QImage")
    qtgui.QGuiApplication = _dummy_class("QGuiApplication")
    qtgui.QDesktopServices = _dummy_class("QDesktopServices")
    qtgui.QAction = _dummy_class("QAction")

    qtweb = types.ModuleType("PySide6.QtWebEngineWidgets")
    qtweb.QWebEngineView = _dummy_class("QWebEngineView")

    sys.modules["PySide6"] = types.ModuleType("PySide6")
    sys.modules["PySide6.QtWidgets"] = qtwidgets
    sys.modules["PySide6.QtCore"] = qtcore
    sys.modules["PySide6.QtGui"] = qtgui
    sys.modules["PySide6.QtWebEngineWidgets"] = qtweb


_install_qt_stubs()

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
