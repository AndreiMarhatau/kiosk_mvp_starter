from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from tests.qt_stubs import install_qt_stubs

install_qt_stubs()

from kiosk_app.app import App  # noqa: E402


class DummyBackend:
    def __init__(self) -> None:
        self.base_url = "http://localhost:9000"
        self.pages: Dict[str, Dict[str, List[dict]]] = {}
        self.requested_pages: List[str] = []

    def build_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def fetch_config(self) -> Dict[str, object]:
        return {
            "org_name": "Test Org",
            "footer_qr_text": "",
            "footer_clock_format": "%H:%M",
            "theme": {},
            "screensaver": {},
        }

    def fetch_menu(self) -> List[dict]:
        return []

    def fetch_page(self, slug: str) -> Dict[str, object]:
        self.requested_pages.append(slug)
        return {"blocks": [{"kind": "text", "content": {"html": slug}}]}

    def verify_exit_password(self, password: str) -> Tuple[bool, str | None]:
        return True, None

    def iter_events(self) -> Iterable[dict]:
        return []


def test_load_model_restores_current_route() -> None:
    backend = DummyBackend()
    app = App(backend=backend)

    app.route("info")
    assert backend.requested_pages[-1] == "info"
    assert app._current_route == "info"

    app.load_model(restore_route="info")

    assert backend.requested_pages[-1] == "info"
    assert app._current_route == "info"
    assert app.stack.currentIndex() == 1


def test_load_model_home_sets_home_index() -> None:
    backend = DummyBackend()
    app = App(backend=backend)

    app.load_model(restore_route="home")

    assert app._current_route == "home"
    assert app.stack.currentIndex() == 0
