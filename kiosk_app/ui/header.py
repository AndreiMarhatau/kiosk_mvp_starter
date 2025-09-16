from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QWidget

from ..backend.media import MediaClient
from ..backend.weather import fetch_weather


class Header(QWidget):
    def __init__(
        self,
        theme: dict,
        org_name: str,
        media: MediaClient,
        *,
        logo_path: Optional[str] = None,
        weather: Optional[dict] = None,
        clock_format: str = "%H:%M",
    ) -> None:
        super().__init__()
        self.theme = theme
        self.media = media
        self.setStyleSheet(f"background:{theme['header_bg']}; color:{theme['text']};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 14, 24, 14)
        layout.setSpacing(12)

        self.logo = QLabel()
        if logo_path:
            pix = self.media.load_pixmap(logo_path)
            if not pix.isNull():
                self.logo.setPixmap(pix.scaledToHeight(36, Qt.SmoothTransformation))
        layout.addWidget(self.logo, 0, Qt.AlignVCenter)
        if logo_path:
            layout.addSpacing(8)

        self.title = QLabel(org_name)
        font = QFont()
        font.setPointSize(26)
        font.setWeight(QFont.DemiBold)
        try:
            font.setUnderline(False)
        except Exception:
            pass
        self.title.setFont(font)
        self.title.setStyleSheet("background: transparent;")
        layout.addWidget(self.title, 0, Qt.AlignVCenter)
        layout.addStretch()

        right = QWidget(self)
        try:
            right.setAttribute(Qt.WA_StyledBackground, True)
        except Exception:
            pass
        right.setAutoFillBackground(False)
        right.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)

        self.weather_label = QLabel("")
        self.weather_label.setStyleSheet("font-size:16px; background: transparent; color: rgba(15,20,25,0.75);")
        self.time_label = QLabel("")
        self.time_label.setStyleSheet("font-size:16px; background: transparent; color: rgba(15,20,25,0.75);")
        right_layout.addWidget(self.weather_label, 0, Qt.AlignRight)
        right_layout.addWidget(self.time_label, 0, Qt.AlignRight)
        layout.addWidget(right, 0, Qt.AlignVCenter)

        self._time_format = clock_format or "%H:%M"
        try:
            timer = QTimer(self)
            timer.timeout.connect(self._tick_time)
            timer.start(1000)
            self._time_timer = timer
        except Exception:
            self._time_timer = None
        self._tick_time()

        self._weather_timer = None
        self._weather_city: Optional[str] = None
        if weather and weather.get("show_weather"):
            self._init_weather(weather.get("weather_city") or "")

    @staticmethod
    def _icon_for_code(code: Optional[int]) -> str:
        try:
            value = int(code) if code is not None else 0
        except Exception:
            value = 0
        if value == 0:
            return "☀"
        if value in (1, 2, 3):
            return "⛅"
        if value in (45, 48):
            return "🌫"
        if 51 <= value <= 57:
            return "🌦"
        if 61 <= value <= 67:
            return "🌧"
        if 71 <= value <= 77:
            return "❄"
        if 80 <= value <= 82:
            return "🌧"
        if 95 <= value <= 99:
            return "⛈"
        return "☁"

    def _init_weather(self, city: str) -> None:
        self._weather_city = city or ""
        try:
            self.weather_label.setText("⛅ …")
        except Exception:
            pass
        self._update_weather()
        try:
            timer = QTimer(self)
            timer.setInterval(10 * 60 * 1000)
            timer.timeout.connect(self._update_weather)
            timer.start()
            self._weather_timer = timer
        except Exception:
            self._weather_timer = None

    def _update_weather(self) -> None:
        if not self._weather_city:
            self.weather_label.setText("")
            return
        city, temperature, code = fetch_weather(self._weather_city)
        if not city:
            self.weather_label.setText("")
            return
        icon = self._icon_for_code(code)
        if isinstance(temperature, (int, float)):
            self.weather_label.setText(f"{city}  {icon} {int(round(temperature))}°C")
        else:
            self.weather_label.setText(f"{city}  {icon}")

    def _tick_time(self) -> None:
        try:
            from datetime import datetime

            now = datetime.now()
            months = [
                "января",
                "февраля",
                "марта",
                "апреля",
                "мая",
                "июня",
                "июля",
                "августа",
                "сентября",
                "октября",
                "ноября",
                "декабря",
            ]
            date_str = f"{now.day} {months[now.month - 1]}"
            time_str = now.strftime(self._time_format or "%H:%M")
            self.time_label.setText(f"{time_str}  •  {date_str}")
        except Exception:
            pass
