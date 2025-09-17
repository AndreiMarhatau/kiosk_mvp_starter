from __future__ import annotations

import hashlib
import os
import tempfile
from typing import Optional

import requests
from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage, QPixmap

_CACHE_DIR = os.path.join(tempfile.gettempdir(), "kiosk_cache")
os.makedirs(_CACHE_DIR, exist_ok=True)


def resolve_url_or_path(path: str, api_base: str) -> str:
    """Convert ``/media/...`` paths into full API URLs."""
    if not path:
        return ""
    if path.startswith("/media/"):
        return f"{api_base}{path}"
    return path


def _cache_http_file(url: str, limit_bytes: Optional[int] = None, timeout: int = 20) -> Optional[str]:
    try:
        key = hashlib.md5(url.encode("utf-8")).hexdigest()
        ext = os.path.splitext(url.split("?")[0])[-1].lower()
        if not ext or len(ext) > 5:
            ext = ".bin"
        target = os.path.join(_CACHE_DIR, f"{key}{ext}")
        if os.path.exists(target) and os.path.getsize(target) > 0:
            return target

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
            )
        }
        with requests.get(url, stream=True, headers=headers, timeout=timeout) as response:
            response.raise_for_status()
            tmp = target + ".part"
            total = 0
            with open(tmp, "wb") as handle:
                for chunk in response.iter_content(chunk_size=256 * 1024):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    total += len(chunk)
                    if limit_bytes and total > limit_bytes:
                        break
            os.replace(tmp, target)
        return target
    except Exception:
        return None


def load_pixmap_any(path: str, api_base: str) -> QPixmap:
    pixmap = QPixmap()
    if not path:
        return pixmap
    url = resolve_url_or_path(path, api_base)
    try:
        if url.startswith("http://") or url.startswith("https://"):
            response = requests.get(url, timeout=7)
            response.raise_for_status()
            image = QImage()
            if image.loadFromData(response.content):
                return QPixmap.fromImage(image)
            return pixmap
        pixmap.load(url)
        return pixmap
    except Exception:
        return QPixmap()


def ensure_local_file_for_pdf(path: str, api_base: str) -> str:
    if not path:
        return ""
    url = resolve_url_or_path(path, api_base)
    if not (url.startswith("http://") or url.startswith("https://")):
        return url
    key = hashlib.md5(url.encode("utf-8")).hexdigest() + ".pdf"
    local_path = os.path.join(_CACHE_DIR, key)
    if not os.path.exists(local_path):
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            with open(local_path, "wb") as handle:
                handle.write(response.content)
        except Exception:
            return ""
    return local_path


def ensure_local_media_file(
    path: str,
    api_base: str,
    *,
    limit_bytes: Optional[int] = 200 * 1024 * 1024,
    timeout: int = 40,
) -> Optional[str]:
    if not path:
        return None
    url = resolve_url_or_path(path, api_base)
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        cached = _cache_http_file(url, limit_bytes=limit_bytes, timeout=timeout)
        return cached or None
    return url.replace("\\", "/")


def url_or_local_for_video(path: str, api_base: str) -> QUrl:
    if not path:
        return QUrl()
    url = resolve_url_or_path(path, api_base)
    if url.startswith("http://") or url.startswith("https://"):
        local_path = _cache_http_file(url)
        if local_path and os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            return QUrl.fromLocalFile(local_path)
        return QUrl(url)
    return QUrl.fromLocalFile(url)


class MediaClient:
    """High level helpers for working with media assets served by the backend."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def resolve(self, path: str) -> str:
        return resolve_url_or_path(path, self.base_url)

    def load_pixmap(self, path: str) -> QPixmap:
        return load_pixmap_any(path, self.base_url)

    def ensure_pdf(self, path: str) -> str:
        return ensure_local_file_for_pdf(path, self.base_url)

    def video_url(self, path: str) -> QUrl:
        return url_or_local_for_video(path, self.base_url)

    def ensure_media(
        self,
        path: str,
        *,
        limit_bytes: Optional[int] = None,
        timeout: int = 40,
    ) -> Optional[str]:
        return ensure_local_media_file(path, self.base_url, limit_bytes=limit_bytes, timeout=timeout)
