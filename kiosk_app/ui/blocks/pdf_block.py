from __future__ import annotations

from typing import Any, Dict

from PySide6.QtWidgets import QLabel

from ...backend.media import MediaClient
from .base import BlockItem, make_placeholder


def create_pdf_block(content: Dict[str, Any], media: MediaClient) -> BlockItem:
    try:
        from PySide6.QtPdf import QPdfDocument
        from PySide6.QtPdfWidgets import QPdfView
    except Exception as exc:  # pragma: no cover - QtPdf unavailable
        return BlockItem(widget=make_placeholder("PDF просмотрщик недоступен", str(exc)))

    pdf_path = media.ensure_pdf(content.get("path", ""))
    if not pdf_path:
        return BlockItem(widget=make_placeholder("Не удалось загрузить PDF", content.get("path", "")))

    view = QPdfView()
    document = QPdfDocument(view)
    try:
        document.load(pdf_path)
        view.setDocument(document)
        view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
    except Exception:
        return BlockItem(widget=make_placeholder("Не удалось загрузить PDF", content.get("path", "")))
    view.setMinimumHeight(620)

    def _cleanup() -> None:
        try:
            document.close()
        except Exception:
            pass
        try:
            document.deleteLater()
        except Exception:
            pass

    return BlockItem(widget=view, cleanup=_cleanup)


__all__ = ["create_pdf_block"]
