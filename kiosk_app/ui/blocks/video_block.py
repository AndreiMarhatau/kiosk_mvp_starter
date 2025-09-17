from __future__ import annotations

import logging
from typing import Any, Dict

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from ...backend.media import MediaClient
from .base import BlockItem, make_placeholder


logger = logging.getLogger(__name__)


def create_video_block(
    content: Dict[str, Any],
    media: MediaClient,
    theme: Dict[str, Any],
    parent: QWidget,
) -> BlockItem:
    try:
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        from PySide6.QtMultimediaWidgets import QVideoWidget
    except Exception as exc:  # pragma: no cover - QtMultimedia unavailable
        return BlockItem(widget=make_placeholder("Видео недоступно", str(exc)))

    container = QWidget(parent)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(int(theme.get("gap", 12)))

    video_widget = QVideoWidget(container)
    try:
        video_widget.setAttribute(Qt.WA_StyledBackground, True)
        video_widget.setStyleSheet(f"background:{theme.get('bg', '#000')};")
        video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    except Exception:
        pass
    video_widget.setMinimumHeight(460)
    layout.addWidget(video_widget)

    status_label = QLabel(container)
    status_label.setWordWrap(True)
    status_label.setAlignment(Qt.AlignCenter)
    status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    status_label.setStyleSheet("font-size:14px; padding:4px;")
    status_label.hide()
    layout.addWidget(status_label)

    player = QMediaPlayer(parent)
    audio = QAudioOutput(parent)
    try:
        audio.setVolume(0.5)
    except Exception:
        pass

    url = media.video_url(content.get("path", ""))
    _bind_video_output(player, video_widget)
    player.setAudioOutput(audio)
    player.setSource(url)

    fallback_added = {"shown": False}

    status_state = {"severity": "info"}

    def _set_status(message: str, *, severity: str = "info") -> None:
        status_state["severity"] = severity if message else "info"
        if not message:
            status_label.hide()
            return
        color_map = {
            "info": theme.get("text_muted", "#9ca3af"),
            "warning": theme.get("warning", "#f59e0b"),
            "error": theme.get("danger", "#ef4444"),
        }
        color = color_map.get(severity, color_map["info"])
        status_label.setStyleSheet(
            f"color:{color}; font-size:14px; padding:4px;"
        )
        status_label.setText(message)
        status_label.show()

    def _show_fallback() -> None:
        if fallback_added["shown"]:
            return
        fallback_added["shown"] = True
        link = QLabel(f"Видео: {content.get('path', '')}")
        link.setStyleSheet("color:#2563eb; text-decoration:underline; font-size:16px;")
        link.setAlignment(Qt.AlignCenter)
        link.setCursor(Qt.PointingHandCursor)
        link.mousePressEvent = lambda _evt: QDesktopServices.openUrl(url)  # type: ignore[assignment]
        layout.addWidget(link)
        _set_status("Видео открывается в отдельном окне", severity="warning")

    if not content.get("path"):
        _set_status("Не указан путь к видео", severity="error")

    try:
        if hasattr(player, "errorOccurred"):
            player.errorOccurred.connect(
                lambda *args: _handle_player_error(player, content, _show_fallback, _set_status, args)
            )
        elif hasattr(player, "errorChanged"):
            player.errorChanged.connect(
                lambda *args: _handle_player_error(player, content, _show_fallback, _set_status, args)
            )
    except Exception:
        pass

    _attach_status_listeners(player, content, _set_status, _show_fallback, status_state)

    try:
        player.play()
        QTimer.singleShot(0, player.play)
    except Exception:
        pass

    container.setMinimumHeight(460)

    def _cleanup() -> None:
        for action in (
            lambda: player.stop(),
            lambda: player.setSource(QUrl()),
            lambda: audio.deleteLater(),
            lambda: player.deleteLater(),
        ):
            try:
                action()
            except Exception:
                pass

    return BlockItem(widget=container, cleanup=_cleanup)


def _handle_player_error(player, content, show_fallback, set_status, args) -> None:
    error_code = args[0] if args else None
    error_text = ""
    try:
        error_text = (player.errorString() or "").strip()
    except Exception:
        pass
    if not error_text and len(args) > 1 and isinstance(args[1], str):
        error_text = args[1].strip()

    path = content.get("path", "") or "(не указан путь)"
    details = error_text
    if not details:
        if hasattr(error_code, "name"):
            details = error_code.name
        elif error_code not in (None, 0):
            details = str(error_code)
    message = "Ошибка воспроизведения видео"
    if details:
        message = f"{message}: {details}"
    set_status(message, severity="error")
    logger.error("Video playback error for %s: %s", path, details or "unknown error")
    show_fallback()


def _attach_status_listeners(player, content, set_status, show_fallback, status_state) -> None:
    try:
        from PySide6.QtMultimedia import QMediaPlayer
    except Exception:
        return

    last_status = {"value": None}

    def _log_status(severity: str, message: str) -> None:
        if not message:
            return
        log_fn = {
            "error": logger.error,
            "warning": logger.warning,
        }.get(severity, logger.info)
        log_fn("Video status for %s: %s", content.get("path", ""), message)

    def _handle_status_change(raw_status) -> None:
        try:
            status_enum = QMediaPlayer.MediaStatus(raw_status)
        except Exception:
            status_enum = raw_status

        if last_status["value"] == status_enum:
            return
        last_status["value"] = status_enum

        severity = "info"
        message = ""

        if status_enum == QMediaPlayer.MediaStatus.NoMedia:
            severity = "error"
            message = "Не указан медиаресурс для видео"
            show_fallback()
        elif status_enum == QMediaPlayer.MediaStatus.LoadingMedia:
            message = "Видео загружается…"
        elif status_enum == QMediaPlayer.MediaStatus.BufferingMedia:
            message = "Видео буферизуется…"
        elif status_enum == QMediaPlayer.MediaStatus.StalledMedia:
            severity = "warning"
            message = "Поток видео остановлен, ожидаем данные"
        elif status_enum == QMediaPlayer.MediaStatus.InvalidMedia:
            severity = "error"
            message = "Неподдерживаемый или поврежденный видеофайл"
            show_fallback()
        elif status_enum == QMediaPlayer.MediaStatus.EndOfMedia:
            message = "Видео завершило воспроизведение"
        elif status_enum in (
            QMediaPlayer.MediaStatus.LoadedMedia,
            QMediaPlayer.MediaStatus.BufferedMedia,
        ):
            message = ""
        elif status_enum == QMediaPlayer.MediaStatus.UnknownMediaStatus:
            message = "Состояние видео неизвестно"
            severity = "warning"
        else:
            # Preserve diagnostic info for unexpected statuses
            message = f"Состояние видео: {status_enum}"
            severity = "warning"

        if message:
            set_status(message, severity=severity)
            _log_status(severity, message)
        else:
            if status_state.get("severity") != "error":
                set_status("")

    def _handle_playback_state(raw_state) -> None:
        try:
            state_enum = QMediaPlayer.PlaybackState(raw_state)
        except Exception:
            state_enum = raw_state

        if state_enum == QMediaPlayer.PlaybackState.PlayingState:
            if status_state.get("severity") != "error":
                set_status("")
        elif state_enum == QMediaPlayer.PlaybackState.PausedState:
            if status_state.get("severity") != "error":
                set_status("Видео на паузе", severity="info")
        elif state_enum == QMediaPlayer.PlaybackState.StoppedState:
            if status_state.get("severity") != "error":
                set_status("Видео остановлено", severity="info")

    try:
        if hasattr(player, "mediaStatusChanged"):
            player.mediaStatusChanged.connect(_handle_status_change)
        if hasattr(player, "playbackStateChanged"):
            player.playbackStateChanged.connect(_handle_playback_state)
    except Exception:
        pass


def _bind_video_output(player, video_widget: QWidget) -> None:
    output_bound = False
    try:
        if hasattr(video_widget, "videoSink"):
            sink = video_widget.videoSink()
            if sink is not None:
                player.setVideoOutput(sink)
                output_bound = True
                logger.debug("Video output bound via videoSink for %s", video_widget)
    except Exception:
        output_bound = False
    if not output_bound:
        try:
            if hasattr(video_widget, "setMediaPlayer"):
                video_widget.setMediaPlayer(player)
                output_bound = True
                logger.debug("Video output bound via setMediaPlayer for %s", video_widget)
        except Exception as exc:
            output_bound = False
            logger.debug("Fallback setMediaPlayer binding failed: %s", exc)
    if not output_bound:
        try:
            player.setVideoOutput(video_widget)
            output_bound = True
            logger.debug("Video output bound directly for %s", video_widget)
        except Exception as exc:
            logger.warning("Не удалось напрямую привязать видеовывод: %s", exc)
    if not output_bound:
        logger.warning("Видео может не отображаться: видеовывод не привязан к %s", type(video_widget))


__all__ = ["create_video_block"]
