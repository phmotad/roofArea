"""Compute roof waters from mask + DSM (slope/aspect). Group by plane, vectorize, area 3D."""

import math
import logging
from dataclasses import dataclass

import numpy as np
from shapely.geometry import Polygon as ShapelyPolygon
import cv2
from skimage import measure
from skimage.measure import find_contours

from roof_api.core.config import settings

logger = logging.getLogger(__name__)

MIN_PIXELS_TO_SPLIT = 150
MIN_ASPECT_DIFF_DEG = 45


@dataclass
class WaterPolygon:
    area_plana_m2: float
    area_real_m2: float
    inclinacao_graus: float
    orientacao_azimute: float
    polygon: ShapelyPolygon
    pixel_area: float
    region_label: int = 0


def _pixel_to_m2(pixel_area: float, bounds: tuple[float, float, float, float], height: int, width: int) -> float:
    """Convert pixel area to m² using bounds (minx, miny, maxx, maxy) and image size."""
    minx, miny, maxx, maxy = bounds
    if width <= 0 or height <= 0:
        return 0.0
    m_per_px_x = abs(maxx - minx) * 111320 * math.cos(math.radians((miny + maxy) / 2)) / width
    m_per_px_y = abs(maxy - miny) * 110540 / height
    m2_per_px = m_per_px_x * m_per_px_y
    return pixel_area * m2_per_px


def _pixel_to_geo_coords(
    coords: np.ndarray,
    bounds: tuple[float, float, float, float],
    height: int,
    width: int,
) -> np.ndarray:
    """coords: Nx2 (row, col). Returns Nx2 (lon, lat)."""
    minx, miny, maxx, maxy = bounds
    if width <= 0 or height <= 0:
        return coords.astype(float)
    col = coords[:, 1]
    row = coords[:, 0]
    lon = minx + (maxx - minx) * col / (width - 1) if width > 1 else minx
    lat = maxy - (maxy - miny) * row / (height - 1) if height > 1 else maxy
    return np.column_stack([lon, lat])


def _coords_to_polygon(
    coords: np.ndarray,
    bounds: tuple[float, float, float, float],
    h: int,
    w: int,
) -> ShapelyPolygon | None:
    """Build polygon from pixel coords via contour. Returns None if invalid."""
    if len(coords) < 3:
        return None
    mask = np.zeros((h, w), dtype=np.uint8)
    r, c = coords[:, 0].astype(int), coords[:, 1].astype(int)
    r = np.clip(r, 0, h - 1)
    c = np.clip(c, 0, w - 1)
    mask[r, c] = 1
    contours = find_contours(mask, 0.5)
    if not contours:
        return None
    contour = max(contours, key=len)
    geo = _pixel_to_geo_coords(contour, bounds, h, w)
    poly = ShapelyPolygon(geo)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly if not poly.is_empty else None


def _mean_aspect_deg(aspect_deg_values: np.ndarray) -> float:
    """Aspect in 0-360; handle wraparound via mean of cos/sin."""
    rad = np.radians(aspect_deg_values)
    m_cos = np.nanmean(np.cos(rad))
    m_sin = np.nanmean(np.sin(rad))
    return (np.degrees(np.arctan2(m_sin, m_cos)) + 360) % 360


def _try_split_region_by_aspect(
    reg,
    aspect_deg: np.ndarray,
    slope_deg: np.ndarray,
    bounds: tuple[float, float, float, float],
    h: int,
    w: int,
    region_label: int,
) -> list[WaterPolygon]:
    """
    If the region has two distinct aspect directions (two roof planes), split into two WaterPolygons.
    Otherwise returns a single-item list (caller will then create one WaterPolygon from reg).
    """
    if reg.area < MIN_PIXELS_TO_SPLIT:
        return []
    coords = reg.coords
    aspect_at = aspect_deg[coords[:, 0], coords[:, 1]]
    if np.any(~np.isfinite(aspect_at)):
        aspect_at = np.nan_to_num(aspect_at, nan=0.0)
    features = np.column_stack([np.cos(np.radians(aspect_at)), np.sin(np.radians(aspect_at))]).astype(np.float32)
    idx = np.random.RandomState(42).permutation(len(features))[:2]
    centers = features[idx].copy()
    for _ in range(20):
        dist0 = np.sum((features - centers[0]) ** 2, axis=1)
        dist1 = np.sum((features - centers[1]) ** 2, axis=1)
        labels = (dist1 < dist0).astype(int)
        n0 = max(1, (labels == 0).sum())
        n1 = max(1, (labels == 1).sum())
        centers[0] = features[labels == 0].mean(axis=0)
        centers[1] = features[labels == 1].mean(axis=0)
    n0, n1 = int((labels == 0).sum()), int((labels == 1).sum())
    if n0 < 30 or n1 < 30:
        return []
    coords0 = coords[labels == 0]
    coords1 = coords[labels == 1]
    mean_asp0 = _mean_aspect_deg(aspect_at[labels == 0])
    mean_asp1 = _mean_aspect_deg(aspect_at[labels == 1])
    diff = abs(mean_asp0 - mean_asp1)
    if diff > 180:
        diff = 360 - diff
    if diff < MIN_ASPECT_DIFF_DEG:
        return []
    poly0 = _coords_to_polygon(coords0, bounds, h, w)
    poly1 = _coords_to_polygon(coords1, bounds, h, w)
    if poly0 is None or poly1 is None:
        return []
    sl0 = float(np.nanmean(slope_deg[coords0[:, 0], coords0[:, 1]]) or 0)
    sl1 = float(np.nanmean(slope_deg[coords1[:, 0], coords1[:, 1]]) or 0)
    area0_px = len(coords0)
    area1_px = len(coords1)
    area_plana_m2_0 = _pixel_to_m2(area0_px, bounds, h, w)
    area_plana_m2_1 = _pixel_to_m2(area1_px, bounds, h, w)
    sl0_rad = math.radians(sl0)
    sl1_rad = math.radians(sl1)
    area_real_0 = area_plana_m2_0 / math.cos(sl0_rad) if sl0_rad >= 1e-6 else area_plana_m2_0
    area_real_1 = area_plana_m2_1 / math.cos(sl1_rad) if sl1_rad >= 1e-6 else area_plana_m2_1
    return [
        WaterPolygon(
            area_plana_m2=area_plana_m2_0,
            area_real_m2=area_real_0,
            inclinacao_graus=sl0,
            orientacao_azimute=mean_asp0,
            polygon=poly0,
            pixel_area=float(area0_px),
            region_label=region_label,
        ),
        WaterPolygon(
            area_plana_m2=area_plana_m2_1,
            area_real_m2=area_real_1,
            inclinacao_graus=sl1,
            orientacao_azimute=mean_asp1,
            polygon=poly1,
            pixel_area=float(area1_px),
            region_label=region_label,
        ),
    ]


def compute_waters(
    mask: np.ndarray,
    dsm: np.ndarray | None,
    bounds: tuple[float, float, float, float],
) -> list[WaterPolygon]:
    """
    mask: HxW bool. dsm: HxW float or None (fallback).
    bounds: (minx, miny, maxx, maxy) WGS84 for area conversion.
    Returns list of WaterPolygon with area_plana_m2, area_real_m2, slope, aspect, polygon.
    """
    h, w = mask.shape[:2]
    if dsm is not None and dsm.shape[:2] != (h, w):
        dsm = cv2.resize(dsm, (w, h), interpolation=cv2.INTER_LINEAR)

    if dsm is not None:
        from roof_api.aguas.slope_aspect import slope_aspect_from_dsm
        slope_deg, aspect_deg = slope_aspect_from_dsm(dsm)
    else:
        slope_deg = np.zeros((h, w), dtype=np.float32)
        aspect_deg = np.zeros((h, w), dtype=np.float32)

    mask_u8 = np.asarray(mask, dtype=np.uint8)
    labeled = measure.label(mask_u8, connectivity=2)
    regions = measure.regionprops(labeled)

    waters: list[WaterPolygon] = []
    for reg in regions:
        if reg.area < 30:
            continue
        region_label = int(reg.label)
        if dsm is not None and reg.area >= MIN_PIXELS_TO_SPLIT:
            split_waters = _try_split_region_by_aspect(
                reg, aspect_deg, slope_deg, bounds, h, w, region_label
            )
            if split_waters:
                waters.extend(split_waters)
                continue
        sl = float(np.nanmean(slope_deg[reg.slice][reg.image]) or 0)
        ap_deg = float(np.nanmean(aspect_deg[reg.slice][reg.image]) or 0)
        sl_rad = math.radians(sl)
        area_plana_px = reg.area
        area_plana_m2 = _pixel_to_m2(area_plana_px, bounds, h, w)
        if sl_rad < 1e-6:
            area_real_m2 = area_plana_m2
        else:
            area_real_m2 = area_plana_m2 / math.cos(sl_rad)
        coords = reg.coords
        if len(coords) < 3:
            continue
        try:
            geo_coords = _pixel_to_geo_coords(coords, bounds, h, w)
            poly = ShapelyPolygon(geo_coords)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if poly.is_empty:
                continue
        except Exception:
            continue
        waters.append(
            WaterPolygon(
                area_plana_m2=area_plana_m2,
                area_real_m2=area_real_m2,
                inclinacao_graus=sl,
                orientacao_azimute=ap_deg,
                polygon=poly,
                pixel_area=area_plana_px,
                region_label=region_label,
            )
        )

    if not waters:
        total_px = int(mask.sum())
        area_plana_m2 = _pixel_to_m2(total_px, bounds, h, w)
        waters = [
            WaterPolygon(
                area_plana_m2=area_plana_m2,
                area_real_m2=area_plana_m2,
                inclinacao_graus=0.0,
                orientacao_azimute=0.0,
                polygon=ShapelyPolygon(),
                pixel_area=float(total_px),
            )
        ]
    return waters
