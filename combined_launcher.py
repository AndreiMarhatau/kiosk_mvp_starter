"""Run the backend API and kiosk UI from a single executable."""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from typing import Iterable


def _resource_path(*relative: str) -> str:
    """Return an absolute path for bundled resources."""

    base = getattr(sys, "_MEIPASS", None)
    if base:
        root = base
    else:
        root = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(root, *relative)


def _ensure_sys_path(paths: Iterable[str]) -> None:
    for path in paths:
        if path and os.path.isdir(path) and path not in sys.path:
            sys.path.insert(0, path)


class BackendServer:
    """Helper that runs uvicorn in a background thread."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        log_level: str = "info",
        startup_timeout: float = 20.0,
    ) -> None:
        import uvicorn

        self.host = host
        self.port = port
        self._startup_timeout = startup_timeout
        self._server = uvicorn.Server(
            uvicorn.Config(
                "backend.app.main:app",
                host=host,
                port=port,
                log_level=log_level,
                reload=False,
            )
        )
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._stop_lock = threading.Lock()
        self._stopped = False

    def start(self) -> None:
        if self._thread.is_alive():
            return

        self._thread.start()
        deadline = time.monotonic() + self._startup_timeout
        while time.monotonic() < deadline:
            if self._server.started:
                return
            if not self._thread.is_alive():
                raise RuntimeError("Backend server thread exited before start-up completed")
            time.sleep(0.1)

        raise TimeoutError("Backend server did not start in time")

    def stop(self, wait: bool = True, timeout: float = 5.0) -> None:
        with self._stop_lock:
            if self._stopped:
                wait = wait and self._thread.is_alive()
            else:
                self._stopped = True
                if self._server:
                    self._server.should_exit = True
        if wait and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            if self._thread.is_alive() and self._server:
                self._server.force_exit = True
                self._thread.join(timeout=1.0)


def _install_qt_message_filter() -> None:
    """Hide noisy Qt log messages that clutter stdout."""

    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    except Exception:  # pragma: no cover - Qt is optional during linting/tests
        return

    previous_handler = None

    def _handler(mode: QtMsgType, context, message: str) -> None:  # type: ignore[override]
        if isinstance(message, str) and "AVStream duration -9223372036854775808 is invalid" in message:
            return
        if previous_handler:
            previous_handler(mode, context, message)  # type: ignore[arg-type]

    previous_handler = qInstallMessageHandler(_handler)


def _run_qt_frontend(server: BackendServer) -> int:
    from PySide6.QtWidgets import QApplication

    from kiosk_app.main import App

    _install_qt_message_filter()

    app = QApplication(sys.argv)

    window = App()
    width = int(os.environ.get("KIOSK_WINDOW_WIDTH", "1280"))
    height = int(os.environ.get("KIOSK_WINDOW_HEIGHT", "800"))
    window.resize(width, height)
    window.show()

    def _shutdown() -> None:
        server.stop()

    app.aboutToQuit.connect(_shutdown)  # type: ignore[arg-type]

    exit_code = 0
    try:
        exit_code = app.exec()
    finally:
        server.stop()
    return exit_code


def _check_backend_health(server: BackendServer, retries: int = 20) -> None:
    import requests

    url = f"http://{server.host}:{server.port}/health"
    for _ in range(retries):
        try:
            response = requests.get(url, timeout=2)
        except requests.RequestException:
            time.sleep(0.5)
            continue
        if response.ok:
            print("Backend health check succeeded.")
            return
        time.sleep(0.5)

    raise RuntimeError("Backend health check failed")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run kiosk backend and UI together.")
    parser.add_argument(
        "--check-backend",
        action="store_true",
        help="Start the backend, perform a health check and exit (no UI).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    base_dir = _resource_path()
    backend_dir = _resource_path("backend")
    kiosk_dir = _resource_path("kiosk_app")
    _ensure_sys_path({base_dir, backend_dir, kiosk_dir})

    # When frozen, ensure the backend uses its bundled data directory
    if backend_dir:
        os.environ.setdefault("KIOSK_BACKEND_BASE", backend_dir)

    server = BackendServer(
        host=os.environ.get("KIOSK_BACKEND_HOST", "127.0.0.1"),
        port=int(os.environ.get("KIOSK_BACKEND_PORT", "8000")),
    )

    try:
        server.start()
        if args.check_backend:
            _check_backend_health(server)
            return 0
        return _run_qt_frontend(server)
    finally:
        server.stop()


if __name__ == "__main__":  # pragma: no cover - manual execution entry point
    sys.exit(main())
