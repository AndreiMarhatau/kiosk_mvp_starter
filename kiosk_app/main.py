import sys, os, tempfile, hashlib, requests, json, time, threading
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QGridLayout, QSizePolicy, QFrame, QScrollArea, QSpacerItem,
    QMenu, QGraphicsDropShadowEffect, QInputDialog, QLineEdit, QDialog, QDialogButtonBox, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QSize, QUrl, QEvent
from PySide6.QtGui import QPixmap, QColor, QFont, QImage, QGuiApplication, QDesktopServices
from PySide6.QtGui import QAction

# Попытка подключить встроенный браузер (WebEngine)
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except Exception:
    QWebEngineView = None

API = "http://127.0.0.1:8000"

# ---------------------- Светлая тема ----------------------
THEME_DEFAULT = {
    "bg": "#f5f7fb",           # общий фон
    "surface": "#ffffff",      # карточки/кнопки
    "header_bg": "#ffffff",
    "footer_bg": "#ffffff",
    "border": "rgba(0,0,0,0.08)",
    "text": "#0f1419",
    "muted": "rgba(15,20,25,0.65)",
    "primary": "#2563eb",      # синий
    "radius": 14,
    "gap": 16,
    "gap_v": 2,
    "tile_min_w": 320,
    "tile_h": 80,
}

# ---------- helpers: media paths / cache / loading ----------
_CACHE_DIR = os.path.join(tempfile.gettempdir(), "kiosk_cache")
os.makedirs(_CACHE_DIR, exist_ok=True)

# Красивый диалог запроса пароля (модульного уровня)
class ExitPwdDialog(QDialog):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Пароль")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            "QDialog{background:%s; border-radius:12px;}"
            "QLabel{font-size:16px;}"
            "QLineEdit{font-size:18px; padding:10px 12px; border:1px solid rgba(0,0,0,0.2); border-radius:8px;}"
            "QPushButton{font-size:16px; padding:8px 14px;}"
            % (THEME_DEFAULT.get('surface', '#ffffff') if not theme else theme.get('surface', '#ffffff'))
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18,18,18,18)
        lay.setSpacing(12)
        title = QLabel("Введите пароль для выхода")
        title.setStyleSheet("font-weight:700; font-size:18px;")
        lay.addWidget(title)
        self.edit = QLineEdit(); self.edit.setEchoMode(QLineEdit.Password); self.edit.setPlaceholderText("Пароль")
        lay.addWidget(self.edit)
        row = QHBoxLayout();
        self.cb = QCheckBox("Показать пароль"); self.cb.stateChanged.connect(lambda _ : self.edit.setEchoMode(QLineEdit.Normal if self.cb.isChecked() else QLineEdit.Password))
        row.addWidget(self.cb); row.addStretch(); lay.addLayout(row)
        self.err = QLabel(""); self.err.setStyleSheet("color:#dc2626; font-size:14px;"); lay.addWidget(self.err)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); lay.addWidget(bb)
        self.resize(420, 200)
    def password(self): return self.edit.text() or ""
    def show_error(self, msg): self.err.setText(msg or "")

def resolve_url_or_path(path: str, api_base: str) -> str:
    """
    Превращает /media/... в абсолютный URL, остальное возвращает как есть.
    """
    if not path:
        return ""
    if path.startswith("/media/"):
        return f"{api_base}{path}"
    return path

def cache_http_file(url: str, limit_bytes: int | None = None, timeout: int = 20) -> str | None:
    """
    Скачивает HTTP/HTTPS ресурс в локальный кеш и возвращает путь к локальному файлу.
    Если не удалось — возвращает None.
    """
    try:
        key = hashlib.md5(url.encode("utf-8")).hexdigest()
        ext = os.path.splitext(url.split("?")[0])[-1].lower()
        if not ext or len(ext) > 5:
            ext = ".bin"
        target = os.path.join(_CACHE_DIR, f"{key}{ext}")
        if os.path.exists(target) and os.path.getsize(target) > 0:
            return target

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
        with requests.get(url, stream=True, headers=headers, timeout=timeout) as r:
            r.raise_for_status()
            tmp = target + ".part"
            total = 0
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=256*1024):
                    if not chunk:
                        continue
                    f.write(chunk)
                    total += len(chunk)
                    if limit_bytes and total > limit_bytes:
                        break
            os.replace(tmp, target)
        return target
    except Exception:
        return None

def load_pixmap_any(path: str, api_base: str) -> QPixmap:
    """
    Загружает картинку по локальному пути или URL (http/https).
    Возвращает QPixmap (может быть пустым, если не удалось).
    """
    pix = QPixmap()
    if not path:
        return pix
    url = resolve_url_or_path(path, api_base)

    try:
        if url.startswith("http://") or url.startswith("https://"):
            r = requests.get(url, timeout=7)
            r.raise_for_status()
            img = QImage()
            if img.loadFromData(r.content):
                return QPixmap.fromImage(img)
            return pix
        else:
            pix.load(url)
            return pix
    except Exception:
        return QPixmap()

def ensure_local_file_for_pdf(path: str, api_base: str) -> str:
    """
    QPdfDocument не умеет http напрямую. Если path URL — скачиваем в кэш и
    возвращаем локальный путь. Если это уже локальный путь — вернём его.
    """
    if not path:
        return ""
    url = resolve_url_or_path(path, api_base)
    if not (url.startswith("http://") or url.startswith("https://")):
        # локальный путь
        return url
    # кэшируем
    key = hashlib.md5(url.encode("utf-8")).hexdigest() + ".pdf"
    loc = os.path.join(_CACHE_DIR, key)
    if not os.path.exists(loc):
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            with open(loc, "wb") as f:
                f.write(r.content)
        except Exception:
            return ""  # пусть выше покажет плейсхолдер
    return loc

def url_or_local_for_video(path: str, api_base: str) -> QUrl:
    """
    Видео умеет http. Если URL — QUrl(url), если локальный — QUrl.fromLocalFile.
    """
    if not path:
        return QUrl()
    url = resolve_url_or_path(path, api_base)
    if url.startswith("http://") or url.startswith("https://"):
        # сначала попробуем скачать и проиграть локально — это устойчивее к 429/частичным ответам
        loc = cache_http_file(url)
        if loc and os.path.exists(loc) and os.path.getsize(loc) > 0:
            return QUrl.fromLocalFile(loc)
        return QUrl(url)
    return QUrl.fromLocalFile(url)

def merge_theme(api_theme: dict | None):
    if not api_theme:
        return THEME_DEFAULT.copy()
    t = THEME_DEFAULT.copy()
    for k in ("bg", "text", "primary"):
        if api_theme.get(k):
            t[k] = api_theme[k]
    return t

def darker(hex_color, factor=0.9):
    c = QColor(hex_color)
    r = max(0, min(255, int(c.red()*factor)))
    g = max(0, min(255, int(c.green()*factor)))
    b = max(0, min(255, int(c.blue()*factor)))
    return QColor(r, g, b).name()

def button_stylesheet(bg, fg="#ffffff", radius=14, pad_v=22, pad_h=22, fs=20):
    hover = darker(bg, 0.92)
    pressed = darker(bg, 0.85)
    return f"""
        QPushButton {{
            background: {bg};
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

def add_shadow(widget, blur=22, x=0, y=8, color="rgba(0,0,0,0.12)"):
    eff = QGraphicsDropShadowEffect()
    eff.setBlurRadius(blur)
    eff.setXOffset(x)
    eff.setYOffset(y)
    eff.setColor(QColor(color))
    widget.setGraphicsEffect(eff)

# ---------------------- Виджеты ----------------------
class Header(QWidget):
    def __init__(self, theme, org_name, logo_path=None, weather: dict | None = None, clock_format: str = "%H:%M"):
        super().__init__()
        self.theme = theme
        self.setStyleSheet(
            f"background:{theme['header_bg']}; color:{theme['text']};"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24,14,24,14); lay.setSpacing(12)

        self.logo = QLabel()
        if logo_path:
            pix = load_pixmap_any(logo_path, API)
            if not pix.isNull():
                self.logo.setPixmap(pix.scaledToHeight(36, Qt.SmoothTransformation))

        self.title = QLabel(org_name)
        f = QFont(); f.setPointSize(26); f.setWeight(QFont.DemiBold)
        try:
            f.setUnderline(False)
        except Exception:
            pass
        self.title.setFont(f)
        self.title.setStyleSheet("background: transparent;")

        lay.addWidget(self.logo, 0, Qt.AlignVCenter)
        if logo_path: lay.addSpacing(8)
        lay.addWidget(self.title, 0, Qt.AlignVCenter)
        lay.addStretch()

        # Right side: weather + time stacked
        right = QWidget(self)
        try:
            right.setAttribute(Qt.WA_StyledBackground, True)
        except Exception:
            pass
        right.setAutoFillBackground(False)
        right.setStyleSheet("background: transparent;")
        right_box = QVBoxLayout(right)
        right_box.setContentsMargins(0,0,0,0)
        right_box.setSpacing(2)
        self.weather_label = QLabel("")
        self.weather_label.setAutoFillBackground(False)
        self.weather_label.setStyleSheet("font-size:16px; background: transparent; color: rgba(15,20,25,0.75);")
        self.time_label = QLabel("")
        self.time_label.setAutoFillBackground(False)
        self.time_label.setStyleSheet("font-size:16px; background: transparent; color: rgba(15,20,25,0.75);")
        right_box.addWidget(self.weather_label, 0, Qt.AlignRight)
        right_box.addWidget(self.time_label, 0, Qt.AlignRight)
        lay.addWidget(right, 0, Qt.AlignVCenter)

        # Time updater
        self._time_format = clock_format or "%H:%M"
        try:
            tt = QTimer(self)
            tt.timeout.connect(self._tick_time)
            tt.start(1000)
            self._time_timer = tt
        except Exception:
            self._time_timer = None
        self._tick_time()

        self._w_timer = None
        if weather and weather.get('show_weather'):
            self._init_weather(weather.get('weather_city') or '')

    def _init_weather(self, city: str):
        self._weather_city = city or ''
        try:
            # Show placeholder immediately so user sees something after save
            self.weather_label.setText("⛅ …")
        except Exception:
            pass
        self._update_weather()
        try:
            t = QTimer(self)
            t.setInterval(10 * 60 * 1000)  # 10 minutes
            t.timeout.connect(self._update_weather)
            t.start()
            self._w_timer = t
        except Exception:
            pass

    @staticmethod
    def _icon_for_code(code: int) -> str:
        try:
            c = int(code)
        except Exception:
            c = 0
        if c == 0: return "☀"
        if c in (1, 2, 3): return "⛅"
        if c in (45, 48): return "🌫"
        if 51 <= c <= 57: return "🌦"
        if 61 <= c <= 67: return "🌧"
        if 71 <= c <= 77: return "❄"
        if 80 <= c <= 82: return "🌧"
        if 95 <= c <= 99: return "⛈"
        return "☁"

    def _update_weather(self):
        city = (getattr(self, '_weather_city', '') or '').strip()
        if not city:
            self.weather_label.setText("")
            return
        try:
            # Geocoding
            ge = requests.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "ru", "format": "json"},
                timeout=6
            ).json()
            results = (ge or {}).get('results') or []
            if not results:
                self.weather_label.setText("")
                return
            r0 = results[0]
            lat = r0.get('latitude'); lon = r0.get('longitude')
            if lat is None or lon is None:
                self.weather_label.setText("")
                return
            # Current weather
            fo = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={"latitude": lat, "longitude": lon, "current_weather": True, "timezone": "auto"},
                timeout=6
            ).json()
            cw = (fo or {}).get('current_weather') or {}
            temp = cw.get('temperature'); code = cw.get('weathercode')
            if temp is None:
                # fallback to new API structure
                current = (fo or {}).get('current') or {}
                temp = (current.get('temperature_2m') if isinstance(current, dict) else None)
                code = (current.get('weather_code') if isinstance(current, dict) else code)
            icon = self._icon_for_code(code if code is not None else 3)
            display_city = r0.get('name') or city
            if isinstance(temp, (int, float)):
                self.weather_label.setText(f"{display_city}  {icon} {int(round(temp))}°C")
            else:
                self.weather_label.setText(f"{display_city}  {icon}")
        except Exception:
            # keep last value; no crash
            pass

    def _tick_time(self):
        try:
            from datetime import datetime
            d = datetime.now()
            months = [
                "января","февраля","марта","апреля","мая","июня",
                "июля","августа","сентября","октября","ноября","декабря"
            ]
            date_str = f"{d.day} {months[d.month-1]}"
            time_str = d.strftime(self._time_format or "%H:%M")
            self.time_label.setText(f"{time_str}  •  {date_str}")
        except Exception:
            pass

class Footer(QWidget):
    def __init__(self, theme, clock_format="%H:%M", qr_text=""):
        super().__init__()
        self.setStyleSheet(
            f"background:{theme['footer_bg']}; color:{theme['muted']};"
            f"border-top:1px solid {theme['border']};"
        )
        self.clock = QLabel(); self.clock.setStyleSheet("font-size:18px; background: transparent;")
        self.qr = QLabel()
        lay = QHBoxLayout(self); lay.setContentsMargins(24,10,24,10)
        lay.addWidget(self.clock); lay.addStretch(); lay.addWidget(self.qr)

        self.format = clock_format
        self.set_qr(qr_text)
        t = QTimer(self); t.timeout.connect(self.tick); t.start(1000); self._timer = t
        self.tick()

    def set_qr(self, text):
        self.qr.clear()
        if not text:
            return
        try:
            import qrcode
            from PIL.ImageQt import ImageQt
            img = qrcode.make(text)
            qim = ImageQt(img)
            pix = QPixmap.fromImage(qim)
            self.qr.setPixmap(pix.scaled(QSize(88,88), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            pass

    def tick(self):
        from datetime import datetime
        self.clock.setText(datetime.now().strftime(self.format))

class KioskTile(QPushButton):
    def __init__(self, title, slug, theme, bg_color=None, on_click=None):
        super().__init__()
        self.slug = slug
        bg = bg_color or theme["primary"]
        self.setStyleSheet(button_stylesheet(bg, pad_v=10))
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(theme["tile_h"])

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 6, 14, 6)
        row.setSpacing(0)

        txt = QLabel(title)
        txt.setStyleSheet("font-size:20px; font-weight:700; background: transparent; color: #ffffff;")
        row.addStretch(1)
        row.addWidget(txt, 0, Qt.AlignCenter)
        row.addStretch(1)
        add_shadow(self, blur=16, y=3)
        if on_click:
            self.clicked.connect(lambda: on_click(self.slug))

class DropList(QWidget):
    def __init__(self, theme, items, on_pick, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.items = items or []
        self.on_pick = on_pick
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        try:
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.setAttribute(Qt.WA_TranslucentBackground, True)
        except Exception:
            pass
        self.setAutoFillBackground(False)
        wrap = QVBoxLayout(self)
        wrap.setContentsMargins(0,0,0,0)
        wrap.setSpacing(0)
        self.setStyleSheet("background: transparent;")
        for it in self.items:
            title = it.get("title","")
            slug = it.get("target_slug","")
            bg = it.get("bg_color") or theme["primary"]
            fg = it.get('text_color') or "#ffffff"
            btn = QPushButton(f"{title}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(button_stylesheet(bg, fg, radius=10, pad_v=14, pad_h=16, fs=18))
            btn.setMinimumWidth(260)
            btn.setMinimumHeight(max(44, theme["tile_h"] - 48))         
            if on_pick:
                btn.clicked.connect(lambda _, s=slug: (self.hide(), on_pick(s)))
            wrap.addWidget(btn)

class GroupTile(QPushButton):
    def __init__(self, title, items, theme, bg_color=None, text_color=None, on_pick=None):
        super().__init__()
        self.theme = theme
        self.items = items or []
        self.on_pick = on_pick
        self.setCursor(Qt.PointingHandCursor)
        bg = bg_color or theme["primary"]
        fg = text_color or "#ffffff"
        self.setStyleSheet(button_stylesheet(bg, fg, pad_v=10))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(theme["tile_h"])

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 6, 14, 6)
        row.setSpacing(0)

        txt = QLabel(title)
        txt.setStyleSheet(f"font-size:20px; font-weight:700; background: transparent; color: {fg};")
        row.addStretch(1)
        row.addWidget(txt, 0, Qt.AlignCenter)
        row.addStretch(1)
        add_shadow(self, blur=16, y=3)

        self.clicked.connect(self._show_list)

    def _show_list(self):
        popup = DropList(self.theme, self.items, self.on_pick, parent=self)
        popup.setFixedWidth(self.width())
        popup.adjustSize()
        pos = self.mapToGlobal(self.rect().bottomLeft())
        x = pos.x(); y = pos.y() + 6
        screen = (self.window().screen().availableGeometry()
                  if hasattr(self.window(), 'screen') and self.window().screen()
                  else QGuiApplication.primaryScreen().availableGeometry())
        w = popup.width(); h = popup.sizeHint().height()
        if x + w > screen.right() - 8:
            x = max(8, screen.right() - 8 - w)
        x = max(8, x)
        if y + h > screen.bottom() - 8:
            y = max(8, screen.bottom() - 8 - h)
        popup.move(x, y)
        popup.show()

class HomePage(QWidget):
    def __init__(self, theme, router):
        super().__init__()
        self.theme = theme
        self.router = router
        self.buttons_data = []
        self.setStyleSheet(f"background:{theme['bg']}; color:{theme['text']};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24,24,24,24)
        outer.setSpacing(theme["gap"])
        # Убираем QScrollArea, чтобы не появлялся вертикальный скролл.
        # Контентная область теперь просто заполняет всё доступное пространство.
        self.wrap = QWidget()
        self.wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer.addWidget(self.wrap, 1)
        self.grid = QGridLayout(self.wrap)
        self.grid.setContentsMargins(0,0,0,0)
        self.grid.setHorizontalSpacing(theme["gap"])
        self.grid.setVerticalSpacing(theme.get("gap_v", theme["gap"]))

    def build(self, top_nodes):
        self.buttons_data = top_nodes
        self._relayout()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self):
        # Correctly clear previous widgets from the grid to avoid
        # them becoming separate top-level windows during resize.
        try:
            while self.grid.count():
                item = self.grid.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.hide()
                    w.setParent(None)
                    w.deleteLater()
        except Exception:
            # Fallback to a safe clear path
            for i in reversed(range(self.grid.count())):
                it = self.grid.itemAt(i)
                w = it.widget() if it else None
                if w is not None:
                    w.hide(); w.setParent(None)
        if not self.buttons_data: return

        w = max(300, self.width() - 48)
        tile_w = self.theme["tile_min_w"]; gap = self.theme["gap"]
        cols = max(1, min(4, (w + gap) // (tile_w + gap)))

        flat = sorted(self.buttons_data, key=lambda x: (x.get("order_index") or 0))
        for idx, node in enumerate(flat):
            r, c = divmod(idx, cols)
            if node.get("kind") == "group":
                tile = GroupTile(
                    title=node.get("title","Группа"),
                    items=node.get("items",[]),
                    theme=self.theme,
                    bg_color=node.get("bg_color"),
                    text_color=node.get("text_color"),
                    on_pick=lambda slug: self.router(slug)
                )
            else:
                tile = KioskTile(
                    title=node.get("title",""),
                    slug=node.get("target_slug",""),
                    theme=self.theme,
                    bg_color=node.get("bg_color"),
                    on_click=lambda slug: self.router(slug)
                )
            self.grid.addWidget(tile, r, c, Qt.AlignTop)

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
class PageView(QWidget):
    def __init__(self, theme, router):
        super().__init__()
        self.theme = theme
        self.router = router
        self.setStyleSheet(f"background:{theme['bg']}; color:{theme['text']};")

        outer = QVBoxLayout(self); outer.setContentsMargins(24,24,24,24); outer.setSpacing(theme["gap"])
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setFrameShape(QFrame.NoFrame)
        # Hide scrollbars (touch scroll still works)
        try:
            self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        except Exception:
            pass
        outer.addWidget(self.scroll, 1)

        self.page_wrap = QWidget(); self.scroll.setWidget(self.page_wrap)
        self.body = QVBoxLayout(self.page_wrap); self.body.setContentsMargins(0,0,0,0); self.body.setSpacing(theme["gap"])
        # media refs store
        self._media_refs = []

        self.home_btn = QPushButton("На главную")
        self.home_btn.setCursor(Qt.PointingHandCursor)
        self.home_btn.setFixedHeight(48)
        self.home_btn.setStyleSheet(
            "background: #e5e7eb; color:#111; border:0; border-radius:10px; font-weight:600; font-size:16px; padding:10px 14px;"
        )
        add_shadow(self.home_btn, blur=16, y=6, color="rgba(0,0,0,0.10)")
        self.home_btn.clicked.connect(lambda: self.router("home"))

        outer.addSpacing(8)
        outer.addWidget(self.home_btn, 0, Qt.AlignRight)

    def render_blocks(self, blocks):
        def clear(l):
            for i in reversed(range(l.count())):
                w = l.itemAt(i).widget()
                if w: w.setParent(None)
        # stop and clear previous media players
        try:
            for p, a, v in self._media_refs:
                try:
                    p.stop()
                except Exception:
                    pass
            self._media_refs.clear()
        except Exception:
            pass
        clear(self.body)

        for blk in blocks:
            kind = blk.get("kind")
            if kind == "text":
                lbl = QLabel(blk["content"].get("html",""))
                lbl.setTextFormat(Qt.RichText)
                lbl.setWordWrap(True)
                lbl.setStyleSheet("font-size:18px; line-height:1.55; background: transparent;")
                self.body.addWidget(lbl)

            elif kind == "image":
                img = QLabel()
                img.setStyleSheet("background: transparent;")
                path = blk["content"].get("path","")
                pix = load_pixmap_any(path, API)
                if not pix.isNull():
                    img.setPixmap(pix.scaledToWidth(1100, Qt.SmoothTransformation))
                else:
                    img.setText(f"Не удалось загрузить изображение:\n{path}")
                    img.setAlignment(Qt.AlignCenter)
                    img.setMinimumHeight(180)
                    img.setStyleSheet("border:1px dashed rgba(0,0,0,0.25); border-radius:10px; font-size:14px; color:#666;")
                self.body.addWidget(img)

            elif kind == "pdf":
                try:
                    from PySide6.QtPdfWidgets import QPdfView
                    from PySide6.QtPdf import QPdfDocument
                    view = QPdfView(); doc = QPdfDocument(view)
                    local_pdf = ensure_local_file_for_pdf(blk["content"].get("path",""), API)
                    if local_pdf:
                        doc.load(local_pdf); view.setDocument(doc)
                        try:
                            view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
                        except Exception:
                            pass
                        view.setMinimumHeight(620)
                        self.body.addWidget(view)
                    else:
                        ph = QLabel(f"Не удалось загрузить PDF:\n{blk['content'].get('path','')}")
                        ph.setAlignment(Qt.AlignCenter)
                        ph.setMinimumHeight(180)
                        ph.setStyleSheet("border:1px dashed rgba(0,0,0,0.25); border-radius:10px; font-size:14px; color:#666;")
                        self.body.addWidget(ph)
                except Exception as e:
                    self.body.addWidget(QLabel(f"PDF просмотрщик недоступен: {e}"))

            elif kind == "video":
                try:
                    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
                    from PySide6.QtMultimediaWidgets import QVideoWidget
                    vw = QVideoWidget(); player = QMediaPlayer(); audio = QAudioOutput()
                    try:
                        vw.setAttribute(Qt.WA_StyledBackground, True)
                        vw.setStyleSheet(f"background:{self.theme['bg']};")
                        vw.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    except Exception:
                        pass
                    try:
                        audio.setVolume(0.5)
                    except Exception:
                        pass
                    url = url_or_local_for_video(blk["content"].get("path",""), API)
                    player.setVideoOutput(vw); player.setAudioOutput(audio); player.setSource(url)
                    # Подстрахуемся: если плеер сообщит об ошибке — покажем ссылку на открытие в браузере
                    try:
                        def _video_error(*_):
                            link = QLabel(f"Видео: {blk['content'].get('path','')}")
                            link.setStyleSheet("color:#2563eb; text-decoration:underline; font-size:16px;")
                            link.setCursor(Qt.PointingHandCursor)
                            link.mousePressEvent = lambda e: QDesktopServices.openUrl(QUrl(blk['content'].get('path','')))
                            self.body.addWidget(link)
                        if hasattr(player, 'errorOccurred'):
                            player.errorOccurred.connect(_video_error)
                        elif hasattr(player, 'errorChanged'):
                            player.errorChanged.connect(_video_error)
                    except Exception:
                        pass

                    player.play()
                    vw.setMinimumHeight(460)
                    self.body.addWidget(vw)
                    # keep refs so GC won't destroy media objects while playing
                    try:
                        self._media_refs.append((player, audio, vw))
                    except Exception:
                        self._media_refs = [(player, audio, vw)]
                except Exception as e:
                    self.body.addWidget(QLabel(f"Видео недоступно: {e}"))

# ---------------------- Приложение ----------------------
class AdminView(QWidget):
    def __init__(self, theme):
        super().__init__()
        self.theme = theme
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(0)
        if QWebEngineView is not None:
            self.view = QWebEngineView(self)
            lay.addWidget(self.view)
        else:
            self.view = None
            lbl = QLabel("Встроенный браузер недоступен. Откроем во внешнем браузере.")
            lbl.setAlignment(Qt.AlignCenter)
            lay.addWidget(lbl)

    
class App(QWidget):
    def __init__(self):
        super().__init__()
        QApplication.setFont(QFont("Segoe UI", 10))
        self.setWindowTitle("Kiosk")

        self.theme = THEME_DEFAULT.copy()

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0,0,0,0)
        self.root_layout.setSpacing(0)

        self.header = Header(self.theme, "Организация")
        self.stack = QStackedWidget()
        self.footer = Footer(self.theme)

        self.root_layout.addWidget(self.header)
        self.root_layout.addWidget(self.stack, 1)
        self.root_layout.addWidget(self.footer)

        self.home = HomePage(self.theme, self.route)
        self.page = PageView(self.theme, self.route)
        self.admin = AdminView(self.theme)
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.page)
        self.stack.addWidget(self.admin)

        self.apply_global_styles()
        self._weather_state = {"show": False, "city": None}
        self.load_model()        # Start SSE listener to get instant updates from Admin
        try:
            t = threading.Thread(target=self._events_loop, daemon=True)
            t.start()
            self._evt_thread = t
        except Exception:
            self._evt_thread = None
        # Periodic check to reflect weather toggle from Admin without manual reload
        try:
            self._cfg_timer = QTimer(self)
            self._cfg_timer.setInterval(5000)
            self._cfg_timer.timeout.connect(self._poll_config_changes)
            self._cfg_timer.start()
        except Exception:
            self._cfg_timer = None
        # Локальное контекстное меню только на окне (без глобального фильтра)
        try:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self._ctx_menu_simple)
        except Exception:
            pass

    def apply_global_styles(self):
        self.setStyleSheet(f"background:{self.theme['bg']}; color:{self.theme['text']};")

    def route(self, slug):
        if slug == "home":
            self.stack.setCurrentIndex(0)
            self.load_home()
            return
        try:
            data = requests.get(f"{API}/pages/{slug}", timeout=7).json()
            self.page.render_blocks(data.get("blocks", []))
            self.stack.setCurrentIndex(1)
        except Exception as e:
            self.page.render_blocks([{"kind":"text","content":{"html":f"<p>Ошибка загрузки страницы: {e}</p>"}}])
            self.stack.setCurrentIndex(1)

    def load_model(self):
        try:
            cfg = requests.get(f"{API}/config", timeout=7).json()
        except Exception:
            cfg = {"org_name":"Организация","footer_qr_text":"","footer_clock_format":"%H:%M","theme":{}}

        self.theme = merge_theme(cfg.get("theme"))

        # Header
        self.root_layout.removeWidget(self.header)
        self.header.deleteLater()
        self.header = Header(self.theme, cfg.get("org_name","Организация"), cfg.get("theme",{}).get("logo_path"))
        self.root_layout.insertWidget(0, self.header)
        try:
            if bool(cfg.get("show_weather")):
                self.header._init_weather(cfg.get("weather_city") or "")
                self._weather_state = {"show": True, "city": (cfg.get("weather_city") or "")}
            else:
                self._weather_state = {"show": False, "city": None}
        except Exception:
            pass
        try:
            self.header._time_format = cfg.get("footer_clock_format","%H:%M") or "%H:%M"
            self.header._tick_time()
        except Exception:
            pass

        # Footer
        self.root_layout.removeWidget(self.footer)
        self.footer.deleteLater()
        self.footer = Footer(self.theme, "", cfg.get("footer_qr_text",""))
        self.root_layout.addWidget(self.footer)

        # Stack
        self.stack.deleteLater()
        self.stack = QStackedWidget()
        self.root_layout.insertWidget(1, self.stack, 1)

        self.home = HomePage(self.theme, self.route)
        self.page = PageView(self.theme, self.route)
        self.admin = AdminView(self.theme)
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.page)
        self.stack.addWidget(self.admin)

        self.apply_global_styles()
        self.load_home()

    def _poll_config_changes(self):
        try:
            cfg = requests.get(f"{API}/config", timeout=6).json()
        except Exception:
            return
        try:
            want_show = bool(cfg.get("show_weather"))
            want_city = (cfg.get("weather_city") or "").strip() or None
            cur_show = self._weather_state.get("show")
            cur_city = self._weather_state.get("city")
            if want_show != cur_show or want_city != cur_city:
                if want_show and want_city:
                    try:
                        self.header._init_weather(want_city)
                    except Exception:
                        pass
                    self._weather_state = {"show": True, "city": want_city}
                else:
                    try:
                        self.header.weather_label.setText("")
                    except Exception:
                        pass
                    self._weather_state = {"show": False, "city": None}
        except Exception:
            pass

    def load_home(self):
        try:
            menu = requests.get(f"{API}/home/menu", timeout=7).json()
        except Exception:
            menu = []
        self.home.build(menu)

    def open_admin(self):
        # Открыть админку во встроенном WebView (если доступен), иначе внешним браузером
        url = f"{API}/login"
        self.admin.load(url)
        # Если есть встроенный браузер, покажем его во фрейме
        if getattr(self.admin, 'view', None) is not None:
            self.stack.setCurrentWidget(self.admin)

    # ---- Global context menu (right-click) ----
    def eventFilter(self, obj, event):
        # Важно: не вызываем super().eventFilter(obj, event),
        # т.к. obj может быть не QObject (например, QWidgetItem) и PySide упадёт по сигнатуре.
        try:
            if event and event.type() == QEvent.ContextMenu:
                self._ctx_menu_simple(event.globalPos())
                return True
        except Exception:
            pass
        # Для всех прочих событий ничего не фильтруем
        return False

    class ExitPasswordDialog(QDialog):
        def __init__(self, theme, parent=None):
            super().__init__(parent)
            self.setModal(True)
            self.setWindowTitle("Пароль")
            self.setAttribute(Qt.WA_StyledBackground, True)
            self.setStyleSheet(
                "QDialog{background:%s; border-radius:12px;}"
                "QLabel{font-size:16px;}"
                "QLineEdit{font-size:18px; padding:10px 12px; border:1px solid rgba(0,0,0,0.2); border-radius:8px;}"
                "QPushButton{font-size:16px; padding:8px 14px;}"
                % (theme.get('surface', '#ffffff'))
            )
            lay = QVBoxLayout(self)
            lay.setContentsMargins(18,18,18,18)
            lay.setSpacing(12)
            title = QLabel("Введите пароль для выхода")
            title.setStyleSheet("font-weight:700; font-size:18px;")
            lay.addWidget(title)
            self.edit = QLineEdit(); self.edit.setEchoMode(QLineEdit.Password); self.edit.setPlaceholderText("Пароль")
            lay.addWidget(self.edit)
            row = QHBoxLayout();
            self.cb = QCheckBox("Показать пароль"); self.cb.stateChanged.connect(lambda _ : self._toggle())
            row.addWidget(self.cb); row.addStretch(); lay.addLayout(row)
            self.err = QLabel(""); self.err.setStyleSheet("color:#dc2626; font-size:14px;"); lay.addWidget(self.err)
            bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); lay.addWidget(bb)
            self.resize(420, 200)
        def _toggle(self):
            self.edit.setEchoMode(QLineEdit.Normal if self.cb.isChecked() else QLineEdit.Password)
        def password(self):
            return self.edit.text() or ""
        def show_error(self, msg):
            self.err.setText(msg or "")
            try:
                QMessageBox.warning(self, 'Ошибка', msg or '')
            except Exception:
                pass

    # (moved) getText monkey-patch is applied at module level below

    def _ctx_menu_simple(self, global_pos):
        menu = QMenu(self)
        # Переключатель полноэкранного
        fs_text = "Открыть полноэкранный режим" if not self.isFullScreen() else "Выйти из полноэкранного режима"
        act_full = QAction(fs_text, self)
        def _toggle_full():
            if self.isFullScreen():
                # Кастомный диалог ввода пароля (с повтором ввода). При ошибке — fallback ниже.
                try:
                    while True:
                        dlg = ExitPwdDialog(getattr(self, 'theme', THEME_DEFAULT), self)
                        if dlg.exec() == QDialog.Accepted:
                            pwd = dlg.password()
                            try:
                                r = requests.post(f"{API}/kiosk/verify-exit", json={'password': pwd}, timeout=7)
                                if r.ok and r.json().get('ok'):
                                    self.showNormal(); return
                                else:
                                    dlg.show_error('Неверный пароль'); continue
                            except Exception:
                                dlg.show_error('Ошибка соединения'); continue
                        else:
                            return
                except Exception:
                    pass
                # запрос пароля у пользователя
                try:
                    pwd, ok = QInputDialog.getText(self, "Пароль", "Введите пароль для выхода:", QLineEdit.Password)
                except Exception:
                    pwd, ok = ("", True)
                if not ok:
                    return
                try:
                    r = requests.post(f"{API}/kiosk/verify-exit", json={"password": pwd}, timeout=7)
                    if r.ok and r.json().get("ok"):
                        self.showNormal()
                    else:
                        # неверный пароль — игнорируем
                        return
                except Exception:
                    return
            else:
                self.showFullScreen()
        act_full.triggered.connect(_toggle_full)
        menu.addAction(act_full)

        # Обновить
        act_reload = QAction("Обновить", self)
        act_reload.triggered.connect(self.load_model)
        menu.addAction(act_reload)

        menu.exec(global_pos)

    def _show_context_menu_inapp(self, global_pos):
        menu = QMenu(self)
        # Полноэкранный режим (переключатель)
        fs_text = "Открыть полноэкранный режим" if not self.isFullScreen() else "Выйти из полноэкранного режима"
        act_full = QAction(fs_text, self)
        def _toggle_full():
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        act_full.triggered.connect(_toggle_full)
        menu.addAction(act_full)

        # Вход в админ‑панель (во встроенном окне)
        act_admin = QAction("Вход в админ‑панель", self)
        act_admin.triggered.connect(self.open_admin)
        menu.addAction(act_admin)

        # Обновить
        act_reload = QAction("Обновить", self)
        act_reload.triggered.connect(self.load_model)
        menu.addAction(act_reload)

        menu.exec(global_pos)

    def _show_context_menu2(self, global_pos):
        menu = QMenu(self)
        # Fullscreen toggle
        fs_text = "Открыть полноэкранный режим" if not self.isFullScreen() else "Выйти из полноэкранного режима"
        act_full = QAction(fs_text, self)
        def _toggle_full():
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        act_full.triggered.connect(_toggle_full)
        menu.addAction(act_full)

       # Refresh
        act_reload = QAction("Обновить", self)
        act_reload.triggered.connect(self.load_model)
        menu.addAction(act_reload)

        menu.exec(global_pos)

    def _show_context_menu(self, global_pos):
        menu = QMenu(self)

        act_full = QAction("Открыть полноэкранный режим", self)
        act_full.triggered.connect(lambda: self.showFullScreen())
        menu.addAction(act_full)

        act_reload = QAction("Обновить", self)
        act_reload.triggered.connect(self.load_model)
        menu.addAction(act_reload)

        menu.exec(global_pos)

# ---- Monkey-patch QInputDialog.getText for custom password dialog ----
try:
    _ORIG_QID_GETTEXT = QInputDialog.getText
except Exception:
    _ORIG_QID_GETTEXT = None

def _kiosk_patched_get_text(parent, title, label, mode=QLineEdit.Normal):
    try:
        theme = getattr(parent, 'theme', THEME_DEFAULT)
        dlg_cls = getattr(App, 'ExitPasswordDialog', None) or ExitPwdDialog
        dlg = dlg_cls(theme, parent)
        ok = (dlg.exec() == QDialog.Accepted)
        return (dlg.password(), ok)
    except Exception:
        if _ORIG_QID_GETTEXT is not None:
            return _ORIG_QID_GETTEXT(parent, title, label, mode)
        try:
            d = ExitPwdDialog(THEME_DEFAULT, parent)
            ok = (d.exec() == QDialog.Accepted)
            return (d.password(), ok)
        except Exception:
            return ("", False)

try:
    QInputDialog.getText = staticmethod(_kiosk_patched_get_text)
except Exception:
    pass

if __name__ == "__main__":
    # Установим фильтр Qt‑логов, чтобы скрыть шум от ffmpeg про duration
    try:
        from PySide6.QtCore import qInstallMessageHandler, QtMsgType
        _prev_qt_handler = None
        def _qt_msg_handler(mode, context, message):
            # Фильтруем известный шум от Qt Multimedia FFmpeg
            if isinstance(message, str) and 'AVStream duration -9223372036854775808 is invalid' in message:
                return
            if _prev_qt_handler:
                _prev_qt_handler(mode, context, message)
        _prev_qt_handler = qInstallMessageHandler(_qt_msg_handler)
    except Exception:
        pass

    app = QApplication(sys.argv)
    w = App()
    w.resize(1280, 800)
    # w.showFullScreen()  # для киоска
    w.show()
    sys.exit(app.exec())
















    def _events_loop(self):
        url = f"{API}/events"
        while True:
            try:
                with requests.get(url, stream=True, timeout=65) as r:
                    if not r.ok:
                        time.sleep(3); continue
                    for raw in r.iter_lines(decode_unicode=True):
                        if raw is None:
                            continue
                        if isinstance(raw, str) and raw.startswith(":"):
                            continue
                        if isinstance(raw, str) and raw.startswith("data:"):
                            data = raw[5:].strip()
                            try:
                                msg = json.loads(data)
                            except Exception:
                                continue
                            typ = (msg or {}).get("type")
                            if typ == "config_updated":
                                QTimer.singleShot(0, self.load_model)
                            elif typ == "menu_updated":
                                QTimer.singleShot(0, self.load_home)
            except Exception:
                time.sleep(3)
