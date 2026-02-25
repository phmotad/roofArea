"""Fetch base imagery (orthophoto, satellite, etc.) for a bounding box."""

import io
import logging
from typing import Tuple

import httpx
import numpy as np
from PIL import Image

from roof_api.geo.bounds import bounds_from_point

logger = logging.getLogger(__name__)


def _fetch_mapbox_static(
    minx: float, miny: float, maxx: float, maxy: float, token: str, size: int = 512
) -> np.ndarray | None:
    """Fetch one image from Mapbox Static Images API for the given bbox. Returns RGB array or None."""
    bbox = f"{minx},{miny},{maxx},{maxy}"
    url = (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
        f"[{bbox}]/{size}x{size}@2x?access_token={token}"
    )
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            return np.array(img)
    except Exception as e:
        logger.warning("Mapbox static fetch failed: %s", e)
        return None


def fetch_ortho(
    lat: float,
    lon: float,
    tile_url: str | None = None,
) -> Tuple[np.ndarray, Tuple[float, float, float, float]]:
    """
    Return (RGB array HxWx3, (minx, miny, maxx, maxy) in WGS84).
    If MAPBOX_ACCESS_TOKEN is set, uses Mapbox Satellite (Static API). Else uses ORTHO_TILE_URL
    or placeholder.
    """
    from roof_api.core.config import settings

    minx, miny, maxx, maxy = bounds_from_point(lat, lon)
    size = 512

    if settings.mapbox_access_token:
        arr = _fetch_mapbox_static(minx, miny, maxx, maxy, settings.mapbox_access_token, size)
        if arr is not None:
            return arr, (minx, miny, maxx, maxy)
        logger.warning("Mapbox failed; falling back to tile URL or placeholder")

    url = tile_url or settings.ortho_tile_url
    if not url:
        logger.warning("No imagery source configured; returning placeholder image")
        arr = np.zeros((size, size, 3), dtype=np.uint8)
        arr[:] = (200, 220, 240)
        return arr, (minx, miny, maxx, maxy)

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content)).convert("RGB")
            return np.array(img), (minx, miny, maxx, maxy)
    except Exception as e:
        logger.warning("Imagery fetch failed: %s; using placeholder", e)
        arr = np.zeros((size, size, 3), dtype=np.uint8)
        arr[:] = (200, 220, 240)
        return arr, (minx, miny, maxx, maxy)
