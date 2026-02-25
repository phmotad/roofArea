"""Cache by (lat, lon). In-memory TTL; extensible to Redis."""

import hashlib
import logging
import time
from roof_api.core.config import settings
from roof_api.services.dtos import AnaliseTelhadoResult

logger = logging.getLogger(__name__)
_memory: dict[str, tuple[AnaliseTelhadoResult, float]] = {}


def _key(lat: float, lon: float) -> str:
    return hashlib.sha256(f"{lat:.6f}_{lon:.6f}".encode()).hexdigest()


async def get_cached_result(lat: float, lon: float) -> AnaliseTelhadoResult | None:
    if settings.cache_ttl_seconds <= 0:
        return None
    k = _key(lat, lon)
    if k not in _memory:
        return None
    result, expiry = _memory[k]
    if time.time() > expiry:
        del _memory[k]
        return None
    return result


async def set_cached_result(lat: float, lon: float, result: AnaliseTelhadoResult) -> None:
    if settings.cache_ttl_seconds <= 0:
        return
    k = _key(lat, lon)
    _memory[k] = (result, time.time() + settings.cache_ttl_seconds)
