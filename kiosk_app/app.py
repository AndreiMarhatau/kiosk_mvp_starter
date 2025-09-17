from __future__ import annotations

import threading
from typing import Dict, Optional

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMenu,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .backend.api import BackendAPI
from .backend.media import MediaClient
from .theme import THEME_DEFAULT, build_background_qss, merge_theme
from .ui import (
    AdminView,
    ExitPwdDialog,
    Footer,
    Header,
    HomePage,
    PageView,
    ScreensaverLayer,
    install_password_dialog_patch,
)


class App(QWidget):
    def __init__(self, backend: Optional[BackendAPI] = None) -> None:
        super().__init__()
        QApplication.setFont(QFont("Segoe UI", 10))
        self.setWindowTitle("Kiosk")

        self.backend = backend or BackendAPI()
        self.media = MediaClient(self.backend.base_url)
        install_password_dialog_patch(lambda: getattr(self, "theme", THEME_DEFAULT))

        self.theme = THEME_DEFAULT.copy()
        self._current_route = "home"

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.header = Header(self.theme, "Организация", self.media)
        self.stack = QStackedWidget()
        self.footer = Footer(self.theme)

        self.root_layout.addWidget(self.header)
        self.root_layout.addWidget(self.stack, 1)
        self.root_layout.addWidget(self.footer)

        self.home = HomePage(self.theme, self.route)
        self.page = PageView(self.theme, self.route, self.media)
        self.admin = AdminView(self.theme)
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.page)
        self.stack.addWidget(self.admin)

        self._screensaver_cfg: Dict[str, object] = {"path": None, "timeout": 0}
        self._screensaver_layer = ScreensaverLayer(self.media, parent=self)
        self._screensaver_layer.set_exit_callback(self._on_screensaver_closed)
        self._screensaver_layer.hide()
        try:
            self._screensaver_layer.setGeometry(self.rect())
        except Exception:
            pass

        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.timeout.connect(self._show_screensaver)

        try:
            QApplication.instance().installEventFilter(self)
        except Exception:
            pass
        self.apply_global_styles()
        self._weather_state: Dict[str, Optional[str]] = {"show": False, "city": None}
        self.load_model()

        try:
            evt_thread = threading.Thread(target=self._events_loop, daemon=True)
            evt_thread.start()
            self._evt_thread = evt_thread
        except Exception:
            self._evt_thread = None

        try:
            cfg_timer = QTimer(self)
            cfg_timer.setInterval(5000)
            cfg_timer.timeout.connect(self._poll_config_changes)
            cfg_timer.start()
            self._cfg_timer = cfg_timer
        except Exception:
            self._cfg_timer = None

        try:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self._ctx_menu_simple)
        except Exception:
            pass

    # ---------------------- Core behaviour ----------------------
    def apply_global_styles(self) -> None:
        self._apply_home_background(self._current_route == "home")

    def _apply_home_background(self, enabled: bool) -> None:
        include_image = enabled and bool(
            self.theme.get("bg_image_local") or self.theme.get("bg_image_path")
        )
        self.setStyleSheet(
            f"{build_background_qss(self.theme, include_image=include_image)} color:{self.theme['text']};"
        )

    def route(self, slug: str) -> None:
        self._handle_user_activity()
        is_home = slug == "home"
        self._current_route = "home" if is_home else slug
        self._apply_home_background(is_home)
        if is_home:
            try:
                self.page.clear()
            except Exception:
                pass
            self.stack.setCurrentIndex(0)
            self.load_home()
            return
        data = self.backend.fetch_page(slug)
        try:
            blocks = data.get("blocks", []) if isinstance(data, dict) else []
            self.page.render_blocks(blocks)
            self.stack.setCurrentIndex(1)
        except Exception as exc:
            self.page.render_blocks([
                {
                    "kind": "text",
                    "content": {"html": f"<p>Ошибка загрузки страницы: {exc}</p>"},
                }
            ])
            self.stack.setCurrentIndex(1)

    def load_model(self, *, restore_route: Optional[str] = None) -> None:
        target_route = restore_route or self._current_route or "home"
        cfg = self.backend.fetch_config()
        theme_payload = cfg.get("theme") if isinstance(cfg, dict) else {}
        self.theme = merge_theme(theme_payload)
        bg_path = (theme_payload or {}).get("bg_image_path") if isinstance(theme_payload, dict) else None
        local_bg = self.media.ensure_media(bg_path, limit_bytes=15 * 1024 * 1024) if bg_path else None
        self.theme["bg_image_path"] = bg_path or None
        self.theme["bg_image_local"] = local_bg

        # Header
        self.root_layout.removeWidget(self.header)
        self.header.deleteLater()
        self.header = Header(
            self.theme,
            cfg.get("org_name", "Организация"),
            self.media,
            logo_path=(cfg.get("theme", {}) or {}).get("logo_path"),
            weather={"show_weather": cfg.get("show_weather"), "weather_city": cfg.get("weather_city")},
            clock_format=cfg.get("footer_clock_format", "%H:%M"),
        )
        self.root_layout.insertWidget(0, self.header)
        show_weather = bool(cfg.get("show_weather"))
        city = (cfg.get("weather_city") or "").strip() or None
        self._weather_state = {"show": show_weather, "city": city}

        # Footer
        self.root_layout.removeWidget(self.footer)
        self.footer.deleteLater()
        self.footer = Footer(
            self.theme,
            cfg.get("footer_clock_format", "%H:%M"),
            cfg.get("footer_qr_text", ""),
        )
        self.root_layout.addWidget(self.footer)

        # Stack
        try:
            if getattr(self, "page", None):
                self.page.clear()
        except Exception:
            pass
        self.stack.deleteLater()
        self.stack = QStackedWidget()
        self.root_layout.insertWidget(1, self.stack, 1)

        self.home = HomePage(self.theme, self.route)
        self.page = PageView(self.theme, self.route, self.media)
        self.admin = AdminView(self.theme)
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.page)
        self.stack.addWidget(self.admin)

        self.apply_global_styles()
        self._update_screensaver_config(cfg.get("screensaver") or {})

        if target_route == "home":
            self._current_route = "home"
            self._apply_home_background(True)
            self.load_home()
            self.stack.setCurrentIndex(0)
        else:
            self.route(target_route)

    def _poll_config_changes(self) -> None:
        cfg = self.backend.fetch_config()
        try:
            want_show = bool(cfg.get("show_weather"))
            want_city = (cfg.get("weather_city") or "").strip() or None
            cur_show = bool(self._weather_state.get("show"))
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

        try:
            screensaver_cfg = cfg.get("screensaver") or {}
            new_path = screensaver_cfg.get("path") or None
            try:
                new_timeout = int(screensaver_cfg.get("timeout") or 0)
            except Exception:
                new_timeout = 0
            current_path = self._screensaver_cfg.get("path")
            current_timeout = int(self._screensaver_cfg.get("timeout") or 0)
            if new_path != current_path or new_timeout != current_timeout:
                self._update_screensaver_config({"path": new_path, "timeout": new_timeout})
        except Exception:
            pass

    def load_home(self) -> None:
        menu = self.backend.fetch_menu()
        self.home.build(menu)

    def open_admin(self) -> None:
        url = self.backend.build_url("/login")
        self.admin.load(url)
        if getattr(self.admin, "view", None) is not None:
            self.stack.setCurrentWidget(self.admin)

    # ---------------------- Context menus ----------------------
    def eventFilter(self, obj, event):  # type: ignore[override]
        try:
            if event and event.type() == QEvent.ContextMenu:
                self._ctx_menu_simple(event.globalPos())
                return True
        except Exception:
            pass
        try:
            if event and event.type() in (
                QEvent.MouseButtonPress,
                QEvent.KeyPress,
                QEvent.TouchBegin,
                QEvent.TouchUpdate,
                QEvent.TouchEnd,
            ):
                self._handle_user_activity()
        except Exception:
            pass
        return False

    def _ctx_menu_simple(self, global_pos) -> None:
        menu = QMenu(self)
        fs_text = "Открыть полноэкранный режим" if not self.isFullScreen() else "Выйти из полноэкранного режима"
        act_full = QAction(fs_text, self)

        def _toggle_full() -> None:
            if self.isFullScreen():
                if self._confirm_exit_fullscreen():
                    self.showNormal()
            else:
                self.showFullScreen()

        act_full.triggered.connect(_toggle_full)
        menu.addAction(act_full)

        act_reload = QAction("Обновить", self)

        def _reload() -> None:
            try:
                current = getattr(self, "_current_route", "home") or "home"
            except Exception:
                current = "home"
            self.load_model(restore_route=current)

        act_reload.triggered.connect(_reload)
        menu.addAction(act_reload)

        menu.exec(global_pos)

    # ---------------------- Screensaver & idle handling ----------------------
    def _handle_user_activity(self) -> None:
        try:
            if self._screensaver_layer and self._screensaver_layer.isVisible():
                self._screensaver_layer.hide_media()
        except Exception:
            pass
        self._reset_idle_timer()

    def _reset_idle_timer(self) -> None:
        try:
            timeout = int(self._screensaver_cfg.get("timeout") or 0)
        except Exception:
            timeout = 0
        path = self._screensaver_cfg.get("path")
        if timeout <= 0 or not path:
            self._idle_timer.stop()
            return
        try:
            self._idle_timer.start(max(1000, timeout * 1000))
        except Exception:
            pass

    def _show_screensaver(self) -> None:
        path = self._screensaver_cfg.get("path")
        if not path:
            return
        try:
            self._idle_timer.stop()
        except Exception:
            pass
        try:
            self._screensaver_layer.setGeometry(self.rect())
        except Exception:
            pass
        try:
            showed = bool(self._screensaver_layer.show_media(path))
        except Exception:
            showed = False
        if showed:
            try:
                self._screensaver_layer.raise_()
            except Exception:
                pass
        else:
            self._reset_idle_timer()

    def _update_screensaver_config(self, data: dict) -> None:
        if not isinstance(data, dict):
            data = {}
        path = data.get("path") or None
        try:
            timeout = int(data.get("timeout") or 0)
        except Exception:
            timeout = 0
        if timeout < 0:
            timeout = 0
        self._screensaver_cfg = {"path": path, "timeout": timeout}
        if not path and self._screensaver_layer and self._screensaver_layer.isVisible():
            try:
                self._screensaver_layer.hide_media()
            except Exception:
                pass
        self._reset_idle_timer()
        self._apply_home_background(self._current_route == "home")

    def _on_screensaver_closed(self) -> None:
        self._reset_idle_timer()

    def resizeEvent(self, event):  # type: ignore[override]
        try:
            if self._screensaver_layer:
                self._screensaver_layer.setGeometry(self.rect())
        except Exception:
            pass
        super().resizeEvent(event)

    def _confirm_exit_fullscreen(self) -> bool:
        while True:
            dialog = ExitPwdDialog(getattr(self, "theme", THEME_DEFAULT), self)
            if dialog.exec() != QDialog.Accepted:
                return False
            password = dialog.password()
            ok, error = self.backend.verify_exit_password(password)
            if ok:
                return True
            dialog.show_error(error or "Неверный пароль")

    # ---------------------- Backend events ----------------------
    def _events_loop(self) -> None:
        for event in self.backend.iter_events():
            try:
                event_type = (event or {}).get("type")
                if event_type == "config_updated":
                    QTimer.singleShot(0, self.load_model)
                elif event_type == "menu_updated":
                    QTimer.singleShot(0, self.load_home)
            except Exception:
                pass
