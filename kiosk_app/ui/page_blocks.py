from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtWidgets import QWidget

from ..backend.media import MediaClient
from .blocks import (
    BlockItem,
    create_image_block,
    create_pdf_block,
    create_text_block,
    create_video_block,
)


def build_block_widget(
    block: dict,
    *,
    theme: dict,
    media: MediaClient,
    router,
    parent: QWidget,
) -> Optional[BlockItem]:
    _ = router  # reserved for future interactive blocks
    kind = (block or {}).get("kind")
    content = (block or {}).get("content") or {}
    if kind == "text":
        return create_text_block(content)
    if kind == "image":
        return create_image_block(content, media)
    if kind == "pdf":
        return create_pdf_block(content, media)
    if kind == "video":
        return create_video_block(content, media, theme, parent)
    return None


__all__ = ["BlockItem", "build_block_widget"]
