from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Dict, Iterator, List, Tuple

import requests

DEFAULT_CONFIG: Dict[str, object] = {
    "org_name": "Организация",
    "footer_qr_text": "",
    "footer_clock_format": "%H:%M",
    "theme": {},
}


@dataclass(slots=True)
class BackendAPI:
    base_url: str = "http://127.0.0.1:9000"

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    def build_url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    # --------- High level REST helpers ---------
    def fetch_config(self) -> Dict[str, object]:
        try:
            response = requests.get(self.build_url("/config"), timeout=7)
            return response.json()
        except Exception:
            return DEFAULT_CONFIG.copy()

    def fetch_menu(self) -> List[dict]:
        try:
            response = requests.get(self.build_url("/home/menu"), timeout=7)
            data = response.json()
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def fetch_page(self, slug: str) -> Dict[str, object]:
        try:
            response = requests.get(self.build_url(f"/pages/{slug}"), timeout=7)
            data = response.json()
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {"blocks": []}

    def verify_exit_password(self, password: str) -> Tuple[bool, str | None]:
        try:
            response = requests.post(
                self.build_url("/kiosk/verify-exit"),
                json={"password": password},
                timeout=7,
            )
            ok = bool(response.ok and (response.json() or {}).get("ok"))
            return ok, None if ok else "Неверный пароль"
        except requests.RequestException:
            return False, "Ошибка соединения"
        except Exception:
            return False, None

    # --------- Server Sent Events ---------
    def iter_events(self) -> Iterator[Dict[str, object]]:
        url = self.build_url("/events")
        while True:
            try:
                with requests.get(url, stream=True, timeout=65) as response:
                    if not response.ok:
                        time.sleep(3)
                        continue
                    for raw in response.iter_lines(decode_unicode=True):
                        if raw is None:
                            continue
                        if isinstance(raw, str) and raw.startswith(":"):
                            continue
                        if isinstance(raw, str) and raw.startswith("data:"):
                            payload = raw[5:].strip()
                            try:
                                message = json.loads(payload)
                            except Exception:
                                continue
                            if isinstance(message, dict):
                                yield message
            except Exception:
                time.sleep(3)
