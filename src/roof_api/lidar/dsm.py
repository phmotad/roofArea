"""Fetch DSM raster for a bounding box. DGT (Portugal), PNOA (Spain). Path can be file or folder."""

import logging
from pathlib import Path
from enum import Enum
from typing import Tuple

import numpy as np

from roof_api.core.config import settings

logger = logging.getLogger(__name__)

DSM_EXTENSIONS = (".tif", ".tiff", ".TIF", ".TIFF")


class LidarSource(Enum):
    DGT = "dgt"
    PNOA = "pnoa"


def _bounds_intersect(
    minx: float, miny: float, maxx: float, maxy: float,
    rminx: float, rminy: float, rmaxx: float, rmaxy: float,
) -> bool:
    return not (maxx < rminx or minx > rmaxx or maxy < rminy or miny > rmaxy)


def _find_raster_containing_bounds(
    folder: Path,
    minx: float, miny: float, maxx: float, maxy: float,
) -> Path | None:
    """Return path to first GeoTIFF in folder whose bounds (WGS84) intersect the request bounds."""
    import rasterio
    from rasterio.warp import transform_bounds
    files = [f for f in folder.rglob("*") if f.suffix in DSM_EXTENSIONS and f.is_file()]
    for p in sorted(files):
        try:
            with rasterio.open(p) as src:
                rb = src.bounds
                if src.crs and src.crs.is_geographic:
                    rminx, rminy, rmaxx, rmaxy = rb.left, rb.bottom, rb.right, rb.top
                else:
                    rminx, rminy, rmaxx, rmaxy = transform_bounds(
                        src.crs, "EPSG:4326", rb.left, rb.bottom, rb.right, rb.top
                    )
                if _bounds_intersect(minx, miny, maxx, maxy, rminx, rminy, rmaxx, rmaxy):
                    return p
        except Exception as e:
            logger.debug("Skip %s: %s", p.name, e)
    return None


def _read_dsm_window(
    path: str | Path,
    minx: float, miny: float, maxx: float, maxy: float,
) -> Tuple[np.ndarray, Tuple[float, float, float, float]] | None:
    """Read DSM window for bounds (WGS84) from one file. Returns (data 2D, bounds WGS84) or None."""
    import rasterio
    from rasterio.windows import from_bounds
    from rasterio.warp import transform_bounds
    try:
        with rasterio.open(path) as src:
            if src.crs and not src.crs.is_geographic:
                l, b, r, t = transform_bounds("EPSG:4326", src.crs, minx, miny, maxx, maxy)
            else:
                l, b, r, t = minx, miny, maxx, maxy
            window = from_bounds(l, b, r, t, src.transform)
            data = src.read(1, window=window)
            return data, (minx, miny, maxx, maxy)
    except Exception as e:
        logger.debug("Read window failed for %s: %s", path, e)
        return None


def get_dsm_for_bounds(
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
) -> Tuple[np.ndarray | None, Tuple[float, float, float, float] | None, LidarSource | None]:
    """
    Return (elevation array 2D, bounds, source) or (None, None, None) if no data.
    path_attr can be a single file path or a folder; if folder, picks the GeoTIFF that contains the bounds.
    """
    import rasterio
    for path_attr, source in [
        (settings.lidar_dgt_path, LidarSource.DGT),
        (settings.lidar_pnoa_path, LidarSource.PNOA),
    ]:
        if not path_attr:
            continue
        p = Path(path_attr)
        if not p.exists():
            logger.debug("DSM path does not exist: %s", path_attr)
            continue
        if p.is_file():
            result = _read_dsm_window(p, minx, miny, maxx, maxy)
        else:
            candidate = _find_raster_containing_bounds(p, minx, miny, maxx, maxy)
            if candidate is None:
                logger.debug("No DSM tile in folder %s contains bounds", path_attr)
                continue
            result = _read_dsm_window(candidate, minx, miny, maxx, maxy)
        if result is not None:
            data, bounds = result
            return data, bounds, source
        logger.debug("DSM %s read failed for bounds", source)

    logger.info("No LIDAR/DSM available for bounds; fallback mode")
    return None, None, None
