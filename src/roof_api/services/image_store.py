"""Store and retrieve generated roof PNG by telhado id. In-memory for MVP."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)
_store: Dict[str, bytes] = {}


def put_image(telhado_id: str, png_bytes: bytes) -> None:
    _store[telhado_id] = png_bytes


def get_image(telhado_id: str) -> bytes | None:
    return _store.get(telhado_id)
