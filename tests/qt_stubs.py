from __future__ import annotations

import sys
import types
from typing import Any, Callable, List, Optional


class _Signal:
    def __init__(self) -> None:
        self._callbacks: List[Callable[..., Any]] = []

    def connect(self, callback: Callable[..., Any]) -> None:
        self._callbacks.append(callback)

    def emit(self, *args: Any, **kwargs: Any) -> None:
        for callback in list(self._callbacks):
            callback(*args, **kwargs)


class _DummyQObject:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._parent = kwargs.get("parent")
        self.destroyed = _Signal()
        
    def setParent(self, parent: Any) -> None:
        self._parent = parent

    def deleteLater(self) -> None:
        self.destroyed.emit(self)


class _LayoutItem:
    def __init__(self, widget: Any = None, layout: Any = None) -> None:
        self._widget = widget
        self._layout = layout

    def widget(self) -> Any:
        return self._widget

    def layout(self) -> Any:
        return self._layout


class QWidget(_DummyQObject):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._children: List[Any] = []
        self._visible = True
        self._style = ""
        self._attributes: dict[int, Any] = {}
        self._title = ""
        self._layout: Optional[object] = None

    def setAttribute(self, key: Any, value: Any) -> None:
        self._attributes[key] = value

    def setStyleSheet(self, style: str) -> None:
        self._style = style

    def setWindowTitle(self, title: str) -> None:
        self._title = title

    def show(self) -> None:
        self._visible = True

    def hide(self) -> None:
        self._visible = False

    def isVisible(self) -> bool:
        return self._visible

    def setVisible(self, value: bool) -> None:
        self._visible = value

    def setWindowFlags(self, _flags: Any) -> None:  # pragma: no cover - no-op
        pass

    def setCursor(self, _cursor: Any) -> None:  # pragma: no cover - no-op
        pass

    def setSizePolicy(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - no-op
        pass

    def setMinimumHeight(self, _value: int) -> None:  # pragma: no cover - no-op
        pass

    def setFixedHeight(self, _value: int) -> None:  # pragma: no cover - no-op
        pass

    def setFixedWidth(self, _value: int) -> None:  # pragma: no cover - no-op
        pass

    def setMinimumSize(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def setAlignment(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def setFocusPolicy(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def setWordWrap(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def setTextFormat(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def setText(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def setPixmap(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def clear(self) -> None:  # pragma: no cover - no-op
        pass

    def raise_(self) -> None:  # pragma: no cover - no-op
        pass

    def setGeometry(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def setAutoFillBackground(self, value: bool) -> None:
        self._auto_fill_background = bool(value)

    def setGraphicsEffect(self, effect: Any) -> None:  # pragma: no cover - store for tests
        self._graphics_effect = effect


class QLabel(QWidget):
    def __init__(self, text: str = "", *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._text = text
        self._font: Optional[QFont] = None  # type: ignore[name-defined]

    def setText(self, text: str) -> None:
        self._text = text

    def text(self) -> str:
        return self._text

    def setFont(self, font: "QFont") -> None:  # type: ignore[name-defined]
        self._font = font

    def font(self) -> Optional["QFont"]:  # type: ignore[name-defined]
        return self._font


class QPushButton(QWidget):
    def __init__(self, text: str = "", *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._text = text
        self.clicked = _Signal()

    def setText(self, text: str) -> None:
        self._text = text

    def click(self) -> None:
        self.clicked.emit()


class QFrame(QWidget):
    NoFrame = 0


class QSizePolicy:
    Expanding = 0
    Fixed = 1


class QVBoxLayout:
    def __init__(self, _parent: Optional[QWidget] = None) -> None:
        self._items: List[_LayoutItem] = []
        self._margins = (0, 0, 0, 0)
        self._spacing = 0
        self._parent = _parent
        if _parent is not None:
            _parent._layout = self

    def setContentsMargins(self, *margins: int) -> None:
        self._margins = margins

    def setSpacing(self, spacing: int) -> None:
        self._spacing = spacing

    def setHorizontalSpacing(self, spacing: int) -> None:
        self._spacing = spacing

    def setVerticalSpacing(self, spacing: int) -> None:
        self._spacing = spacing

    def setAlignment(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - no-op
        pass

    def addWidget(self, widget: QWidget, *_args: Any) -> None:
        self._items.append(_LayoutItem(widget=widget))

    def addLayout(self, layout: "QVBoxLayout", *_args: Any) -> None:
        self._items.append(_LayoutItem(layout=layout))

    def removeWidget(self, widget: QWidget) -> None:
        self._items = [item for item in self._items if item.widget() is not widget]

    def addSpacing(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def addStretch(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def insertWidget(self, index: int, widget: QWidget, *_args: Any) -> None:
        self._items.insert(index, _LayoutItem(widget=widget))

    def count(self) -> int:
        return len(self._items)

    def takeAt(self, index: int) -> Optional[_LayoutItem]:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def itemAt(self, index: int) -> Optional[_LayoutItem]:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None


class _ScrollBar:
    def __init__(self) -> None:
        self._value = 0

    def setValue(self, value: int) -> None:
        self._value = value

    def value(self) -> int:
        return self._value


class QScrollArea(QWidget):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._widget: Optional[QWidget] = None
        self._vertical_bar = _ScrollBar()
        self._horizontal_bar = _ScrollBar()

    def setWidgetResizable(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def setFrameShape(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def setVerticalScrollBarPolicy(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def setHorizontalScrollBarPolicy(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass

    def setWidget(self, widget: QWidget) -> None:
        self._widget = widget
        if widget is not None:
            widget.setParent(self)

    def widget(self) -> Optional[QWidget]:
        return self._widget

    def verticalScrollBar(self) -> "_ScrollBar":
        return self._vertical_bar

    def horizontalScrollBar(self) -> "_ScrollBar":
        return self._horizontal_bar

    def ensureVisible(self, x: int, y: int) -> None:  # pragma: no cover - set tracked values
        self._horizontal_bar.setValue(x)
        self._vertical_bar.setValue(y)


class QStackedWidget(QWidget):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._widgets: List[QWidget] = []
        self._current_index = 0

    def addWidget(self, widget: QWidget) -> None:
        self._widgets.append(widget)

    def setCurrentIndex(self, index: int) -> None:
        self._current_index = index

    def setCurrentWidget(self, widget: QWidget) -> None:
        if widget in self._widgets:
            self._current_index = self._widgets.index(widget)

    def currentIndex(self) -> int:
        return self._current_index


class QMenu(QWidget):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._actions: List[QAction] = []

    def addAction(self, action: "QAction") -> None:
        self._actions.append(action)

    def exec(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - no-op
        pass


class QAction(_DummyQObject):
    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)
        self.text = text
        self.triggered = _Signal()


class QDialog(QWidget):
    Accepted = 1
    Rejected = 0

    def exec(self) -> int:
        return QDialog.Rejected


class QApplication:
    _instance: Optional["QApplication"] = None

    def __init__(self, *_args: Any) -> None:
        QApplication._instance = self

    @staticmethod
    def instance() -> Optional["QApplication"]:
        return QApplication._instance

    @staticmethod
    def setFont(_font: Any) -> None:  # pragma: no cover - no-op
        pass

    def installEventFilter(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass


class QUrl:
    def __init__(self, path: str = "") -> None:
        self._path = path

    def toString(self) -> str:  # pragma: no cover - helper for tests
        return self._path

    @staticmethod
    def fromLocalFile(path: str) -> "QUrl":
        return QUrl(path)


class QTimer(_DummyQObject):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._interval = 0
        self.timeout = _Signal()
        self._single_shot = False
        self._running = False

    def setInterval(self, interval: int) -> None:
        self._interval = interval

    def setSingleShot(self, single: bool) -> None:
        self._single_shot = single

    def start(self, *_args: Any) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    @staticmethod
    def singleShot(_msec: int, callback: Callable[[], None]) -> None:
        callback()


class QMovie(_DummyQObject):
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        super().__init__()
        self._valid = True

    def isValid(self) -> bool:
        return self._valid

    def start(self) -> None:  # pragma: no cover - no-op
        pass


class QColor:
    def __init__(self, *args: Any) -> None:
        self._r = 0
        self._g = 0
        self._b = 0
        if len(args) == 1 and isinstance(args[0], str):
            value = args[0]
            if value.startswith("#") and len(value) == 7:
                self._r = int(value[1:3], 16)
                self._g = int(value[3:5], 16)
                self._b = int(value[5:7], 16)
        elif len(args) == 3:
            self._r, self._g, self._b = [int(a) for a in args]

    def red(self) -> int:
        return self._r

    def green(self) -> int:
        return self._g

    def blue(self) -> int:
        return self._b

    def name(self) -> str:
        return f"#{self._r:02x}{self._g:02x}{self._b:02x}"


class QGraphicsDropShadowEffect(_DummyQObject):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.blur = 0
        self.offset = (0, 0)
        self.color = None

    def setBlurRadius(self, value: int) -> None:
        self.blur = value

    def setXOffset(self, value: int) -> None:
        self.offset = (value, self.offset[1])

    def setYOffset(self, value: int) -> None:
        self.offset = (self.offset[0], value)

    def setColor(self, color: QColor) -> None:
        self.color = color


class QPixmap:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self._null = False

    @staticmethod
    def fromImage(_image: Any) -> "QPixmap":
        return QPixmap()

    def scaled(self, *_args: Any, **_kwargs: Any) -> "QPixmap":
        return self

    def scaledToWidth(self, *_args: Any, **_kwargs: Any) -> "QPixmap":
        return self

    def scaledToHeight(self, *_args: Any, **_kwargs: Any) -> "QPixmap":
        return self

    def isNull(self) -> bool:
        return self._null

    def load(self, *_args: Any, **_kwargs: Any) -> None:
        self._null = False


class QImage:
    def loadFromData(self, *_args: Any, **_kwargs: Any) -> bool:
        return True


class QFont:
    DemiBold = 600

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self._point_size = 0
        self._bold = False
        self._weight = 0

    def setPointSize(self, size: int) -> None:
        self._point_size = size

    def pointSize(self) -> int:
        return self._point_size

    def setBold(self, value: bool) -> None:
        self._bold = bool(value)

    def bold(self) -> bool:
        return self._bold

    def setWeight(self, weight: int) -> None:
        self._weight = weight

    def weight(self) -> int:
        return self._weight


class _QtNamespace:
    AlignCenter = 0
    AlignRight = 0
    AlignTop = 0
    AlignVCenter = 0
    KeepAspectRatio = 0
    SmoothTransformation = 0
    PointingHandCursor = 0
    ScrollBarAlwaysOff = 0
    RichText = 0
    WA_StyledBackground = 0
    WA_AcceptTouchEvents = 0
    WA_TranslucentBackground = 0
    Widget = 0
    FramelessWindowHint = 0
    Popup = 0
    NoDropShadowWindowHint = 0
    NoFocus = 0


class QPdfDocument(_DummyQObject):
    instances: List["QPdfDocument"] = []

    def __init__(self, *_args: Any, **kwargs: Any) -> None:
        super().__init__(*_args, **kwargs)
        self.loaded_path: Optional[str] = None
        self.closed = False
        self.deleted = False
        QPdfDocument.instances.append(self)

    def load(self, path: str) -> None:
        self.loaded_path = path

    def close(self) -> None:
        self.closed = True

    def deleteLater(self) -> None:
        self.deleted = True
        super().deleteLater()


class QPdfView(QWidget):
    ZoomMode = types.SimpleNamespace(FitToWidth=0)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.document: Optional[QPdfDocument] = None

    def setDocument(self, document: QPdfDocument) -> None:
        self.document = document

    def setZoomMode(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass


class _VideoSink:
    def __init__(self, widget: "QVideoWidget") -> None:
        self.widget = widget


class QVideoWidget(QWidget):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._minimum_height = 0
        self._media_player: Optional[QMediaPlayer] = None  # type: ignore[name-defined]
        self._sink = _VideoSink(self)

    def setMinimumHeight(self, value: int) -> None:
        self._minimum_height = value

    def setMediaPlayer(self, player: "QMediaPlayer") -> None:  # type: ignore[name-defined]
        self._media_player = player

    def mediaPlayer(self) -> Optional["QMediaPlayer"]:  # type: ignore[name-defined]
        return self._media_player

    def videoSink(self) -> _VideoSink:
        return self._sink


class QAudioOutput(_DummyQObject):
    instances: List["QAudioOutput"] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.volume = 1.0
        QAudioOutput.instances.append(self)

    def setVolume(self, volume: float) -> None:
        self.volume = volume

    def deleteLater(self) -> None:
        super().deleteLater()


class QMediaPlayer(_DummyQObject):
    instances: List["QMediaPlayer"] = []

    class Loops:
        Infinite = -1

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.video_output: Optional[object] = None
        self.audio_output: Optional[QAudioOutput] = None
        self.source: Optional[QUrl] = None
        self.play_called = 0
        self.stop_called = 0
        self.deleted = False
        self.timeout = 0
        self.errorOccurred = _Signal()
        self.errorChanged = _Signal()
        QMediaPlayer.instances.append(self)

    def setVideoOutput(self, output) -> None:  # type: ignore[override]
        self.video_output = output
        if hasattr(output, "widget"):
            widget = getattr(output, "widget")
            if hasattr(widget, "setMediaPlayer"):
                widget.setMediaPlayer(self)
        elif hasattr(output, "setMediaPlayer"):
            output.setMediaPlayer(self)

    def setAudioOutput(self, audio: QAudioOutput) -> None:
        self.audio_output = audio

    def setSource(self, url: QUrl) -> None:
        self.source = url

    def play(self) -> None:
        self.play_called += 1

    def stop(self) -> None:
        self.stop_called += 1

    def deleteLater(self) -> None:
        self.deleted = True
        super().deleteLater()

    def setLoops(self, *_args: Any) -> None:  # pragma: no cover - no-op
        pass


class QDesktopServices:
    last_url: Optional[QUrl] = None

    @staticmethod
    def openUrl(url: QUrl) -> None:
        QDesktopServices.last_url = url


Qt = _QtNamespace()


class QGuiApplication:
    @staticmethod
    def primaryScreen() -> None:  # pragma: no cover - no-op
        return None


def install_qt_stubs() -> None:
    if "PySide6" in sys.modules:
        return

    qtwidgets = types.ModuleType("PySide6.QtWidgets")
    qtwidgets.QApplication = QApplication
    qtwidgets.QWidget = QWidget
    qtwidgets.QVBoxLayout = QVBoxLayout
    qtwidgets.QHBoxLayout = QVBoxLayout
    qtwidgets.QLabel = QLabel
    qtwidgets.QPushButton = QPushButton
    qtwidgets.QScrollArea = QScrollArea
    qtwidgets.QSizePolicy = QSizePolicy
    qtwidgets.QFrame = QFrame
    qtwidgets.QStackedWidget = QStackedWidget
    qtwidgets.QMenu = QMenu
    qtwidgets.QAction = QAction
    qtwidgets.QDialog = QDialog
    qtwidgets.QGridLayout = QVBoxLayout
    qtwidgets.QSpacerItem = object
    qtwidgets.QGraphicsDropShadowEffect = QGraphicsDropShadowEffect
    qtwidgets.QInputDialog = object
    qtwidgets.QLineEdit = types.SimpleNamespace(Normal=0, Password=1)
    qtwidgets.QDialogButtonBox = types.SimpleNamespace(Ok=1, Cancel=2)
    qtwidgets.QCheckBox = QWidget
    qtwidgets.QMessageBox = types.SimpleNamespace(warning=lambda *args, **kwargs: None)

    qtcore = types.ModuleType("PySide6.QtCore")
    qtcore.Qt = Qt
    qtcore.QTimer = QTimer
    qtcore.QSize = object
    qtcore.QUrl = QUrl
    qtcore.QEvent = types.SimpleNamespace(
        ContextMenu=0,
        MouseButtonPress=1,
        KeyPress=2,
        TouchBegin=3,
        TouchUpdate=4,
        TouchEnd=5,
    )

    qtgui = types.ModuleType("PySide6.QtGui")
    qtgui.QPixmap = QPixmap
    qtgui.QColor = QColor
    qtgui.QFont = QFont
    qtgui.QImage = QImage
    qtgui.QGuiApplication = QGuiApplication
    qtgui.QDesktopServices = QDesktopServices
    qtgui.QAction = QAction
    qtgui.QMovie = QMovie

    qtmultimedia = types.ModuleType("PySide6.QtMultimedia")
    qtmultimedia.QMediaPlayer = QMediaPlayer
    qtmultimedia.QAudioOutput = QAudioOutput

    qtmultimediawidgets = types.ModuleType("PySide6.QtMultimediaWidgets")
    qtmultimediawidgets.QVideoWidget = QVideoWidget

    qtpdf = types.ModuleType("PySide6.QtPdf")
    qtpdf.QPdfDocument = QPdfDocument

    qtpdfwidgets = types.ModuleType("PySide6.QtPdfWidgets")
    qtpdfwidgets.QPdfView = QPdfView

    qtweb = types.ModuleType("PySide6.QtWebEngineWidgets")
    qtweb.QWebEngineView = QWidget

    qtsvg = types.ModuleType("PySide6.QtSvg")
    qtsvg.QSvgWidget = QWidget

    pysid = types.ModuleType("PySide6")

    sys.modules["PySide6"] = pysid
    sys.modules["PySide6.QtWidgets"] = qtwidgets
    sys.modules["PySide6.QtCore"] = qtcore
    sys.modules["PySide6.QtGui"] = qtgui
    sys.modules["PySide6.QtMultimedia"] = qtmultimedia
    sys.modules["PySide6.QtMultimediaWidgets"] = qtmultimediawidgets
    sys.modules["PySide6.QtPdf"] = qtpdf
    sys.modules["PySide6.QtPdfWidgets"] = qtpdfwidgets
    sys.modules["PySide6.QtWebEngineWidgets"] = qtweb
    sys.modules["PySide6.QtSvg"] = qtsvg

    if "requests" not in sys.modules:
        class _Response:
            def __init__(self, json_data: Optional[dict[str, Any]] = None, content: bytes | None = None) -> None:
                self._json = json_data or {}
                self.content = content or b""
                self.ok = True
                self.status_code = 200

            def json(self) -> dict[str, Any]:
                return self._json

            def raise_for_status(self) -> None:  # pragma: no cover - simple stub
                if not self.ok:
                    raise Exception("request failed")

            def iter_content(self, chunk_size: int = 1):  # pragma: no cover - yields once
                yield b""

            def iter_lines(self, decode_unicode: bool = False):  # pragma: no cover - yields nothing
                if decode_unicode:
                    return iter([""])
                return iter([b""])

        class _ResponseCM(_Response):
            def __enter__(self) -> "_ResponseCM":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        def _get(*_args: Any, **_kwargs: Any) -> _ResponseCM:
            return _ResponseCM()

        def _post(*_args: Any, **_kwargs: Any) -> _ResponseCM:
            data = _kwargs.get("json") or {}
            return _ResponseCM(json_data={"ok": data.get("ok", True)})

        requests_stub = types.ModuleType("requests")
        requests_stub.get = _get
        requests_stub.post = _post
        requests_stub.RequestException = Exception

        sys.modules["requests"] = requests_stub


__all__ = ["install_qt_stubs"]
