"""Orchestrate full pipeline: ortho -> segment -> DSM -> waters -> persist -> image."""

import base64
import logging
from uuid import uuid4
from datetime import datetime, timezone

import math
import numpy as np
import cv2
from shapely.geometry import Point as ShapelyPoint
from skimage import measure
from geoalchemy2 import WKTElement

from roof_api.services.dtos import AnaliseTelhadoResult, AguaDto
from roof_api.db.models import Telhado, AguaTelhado
from roof_api.db.session import async_session_factory
from roof_api.core.config import settings
from roof_api.geo import fetch_ortho
from roof_api.lidar import get_dsm_for_bounds, LidarSource
from roof_api.segmentation import segment_roof_mask, segment_lines_map, segment_waters_mask
from roof_api.aguas import compute_waters
from roof_api.visualization import render_roof_image
from roof_api.services.cache import get_cached_result, set_cached_result
from roof_api.services.image_store import put_image

logger = logging.getLogger(__name__)


def _iter_polygon_exteriors(geom):
    """Yield exterior coords for each polygon part (Polygon or MultiPolygon)."""
    if geom.is_empty:
        return
    if hasattr(geom, "exterior") and geom.exterior is not None and len(geom.exterior.coords) >= 3:
        yield np.array(geom.exterior.coords, dtype=np.float64)
    elif hasattr(geom, "geoms"):
        for part in geom.geoms:
            yield from _iter_polygon_exteriors(part)


def _mask_from_waters(waters, bounds: tuple[float, float, float, float], h: int, w: int) -> np.ndarray:
    """Rasterize water polygons to a binary mask (for contour when filtering by distance)."""
    minx, miny, maxx, maxy = bounds
    span_x = max(maxx - minx, 1e-9)
    span_y = max(maxy - miny, 1e-9)
    out = np.zeros((h, w), dtype=np.uint8)
    for wa in waters:
        if wa.polygon.is_empty or wa.polygon.bounds is None:
            continue
        for pts in _iter_polygon_exteriors(wa.polygon):
            if pts.shape[0] < 3:
                continue
            col = np.clip((pts[:, 0] - minx) / span_x * (w - 1), 0, w - 1)
            row = np.clip((maxy - pts[:, 1]) / span_y * (h - 1), 0, h - 1)
            pts_px = np.column_stack([col, row]).astype(np.int32)
            cv2.fillPoly(out, [pts_px], 1)
    return out


async def analyse_roof(lat: float, lon: float) -> AnaliseTelhadoResult:
    """
    Run full pipeline; persist to DB; return DTO. Uses cache when enabled.
    Raises ValueError for invalid coords or no data; ConnectionError for service failure.
    """
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Coordenadas inválidas")

    cached = await get_cached_result(lat, lon)
    if cached is not None:
        return cached

    rgb, bounds = fetch_ortho(lat, lon)
    minx, miny, maxx, maxy = bounds
    mask = segment_roof_mask(rgb)
    lines_map = segment_lines_map(rgb)
    waters_mask = segment_waters_mask(rgb)
    dsm, _, lidar_source = get_dsm_for_bounds(minx, miny, maxx, maxy)
    waters_all = compute_waters(mask, dsm, bounds, lines_map=lines_map)
    # Fluxo: (lat,lon) deve bater em cima de um telhado -> selecionar só esse componente (área >= min_roof_area_m2) -> área total só desse telhado
    h, w = mask.shape[:2]
    min_area_m2 = settings.min_roof_area_m2
    pt = ShapelyPoint(lon, lat)
    labeled = measure.label(np.asarray(mask, dtype=np.uint8), connectivity=2)
    waters_containing = [
        wa for wa in waters_all
        if not wa.polygon.is_empty and wa.polygon.contains(pt) and wa.area_real_m2 >= min_area_m2
    ]
    if waters_containing:
        label_at_point = waters_containing[0].region_label
    else:
        col = (lon - minx) / (maxx - minx) * (w - 1) if maxx != minx else 0
        row = (maxy - lat) / (maxy - miny) * (h - 1) if maxy != miny else 0
        ri = max(0, min(h - 1, int(round(row))))
        ci = max(0, min(w - 1, int(round(col))))
        label_at_point = int(labeled[ri, ci]) if 0 <= ri < h and 0 <= ci < w else 0
        if label_at_point == 0:
            valid_waters = [wa for wa in waters_all if not wa.polygon.is_empty and wa.area_real_m2 >= min_area_m2]
            if valid_waters:
                nearest = min(valid_waters, key=lambda wa: wa.polygon.distance(pt))
                label_at_point = nearest.region_label
    if label_at_point == 0:
        raise ValueError("Nenhum telhado nas coordenadas indicadas")
    waters = [wa for wa in waters_all if wa.region_label == label_at_point]
    max_dist_m = getattr(settings, "max_roof_distance_from_point_m", 0.0) or 0.0
    if max_dist_m > 0 and waters:
        m_per_deg_lat = 110540.0
        m_per_deg_lon = 111320.0 * math.cos(math.radians(lat))
        waters_near = []
        for wa in waters:
            if wa.polygon.is_empty or wa.polygon.centroid is None:
                continue
            c = wa.polygon.centroid
            dy_m = (lat - c.y) * m_per_deg_lat
            dx_m = (lon - c.x) * m_per_deg_lon
            dist_m = (dx_m * dx_m + dy_m * dy_m) ** 0.5
            if dist_m <= max_dist_m:
                waters_near.append(wa)
        if waters_near:
            waters = waters_near
    if not waters:
        raise ValueError("Nenhum telhado nas coordenadas indicadas")
    area_total_m2 = sum(wa.area_real_m2 for wa in waters)
    if area_total_m2 < min_area_m2:
        raise ValueError("Nenhum telhado nas coordenadas indicadas")
    if max_dist_m > 0:
        mask_roof = _mask_from_waters(waters, bounds, h, w)
    else:
        mask_roof = (labeled == label_at_point).astype(np.uint8)
    png_bytes = render_roof_image(
        rgb, mask_roof, waters, bounds,
        lines_map=lines_map,
        waters_mask=waters_mask,
        only_waters=getattr(settings, "render_only_waters", False),
    )

    telhado_id = str(uuid4())
    put_image(telhado_id, png_bytes)
    processado_em = datetime.now(timezone.utc)
    ponto_wkt = f"POINT({lon} {lat})"
    bounds_wkt = f"POLYGON(({minx} {miny},{maxx} {miny},{maxx} {maxy},{minx} {maxy},{minx} {miny}))"

    agua_ids: list[str] = []
    async with async_session_factory() as session:
        telhado = Telhado(
            id=telhado_id,
            lat=lat,
            lon=lon,
            area_total_m2=area_total_m2,
            ponto=WKTElement(ponto_wkt, srid=4326),
            bounds=WKTElement(bounds_wkt, srid=4326),
            processado_em=processado_em,
            fonte_lidar=lidar_source.name if lidar_source else None,
        )
        session.add(telhado)
        for ordem, w in enumerate(waters):
            agua_id = str(uuid4())
            agua_ids.append(agua_id)
            if w.polygon.is_empty:
                geom_wkt = "MULTIPOLYGON EMPTY"
            else:
                geom_wkt = w.polygon.wkt
            agua = AguaTelhado(
                id=agua_id,
                telhado_id=telhado_id,
                area_plana_m2=w.area_plana_m2,
                area_real_m2=w.area_real_m2,
                inclinacao_graus=w.inclinacao_graus,
                orientacao_azimute=w.orientacao_azimute,
                geometria=WKTElement(geom_wkt, srid=4326),
                ordem=ordem,
            )
            session.add(agua)
        await session.commit()

    imagem_url = f"/telhados/{telhado_id}/imagem.png"
    imagem_base64 = base64.b64encode(png_bytes).decode("utf-8") if settings.output_image_base64 else None

    aguas_dto = [
        AguaDto(
            id=aid,
            area_real_m2=w.area_real_m2,
            inclinacao_graus=w.inclinacao_graus,
            orientacao_azimute=w.orientacao_azimute,
            geometria_wkt=w.polygon.wkt if not w.polygon.is_empty else "POLYGON EMPTY",
        )
        for aid, w in zip(agua_ids, waters)
    ]

    result = AnaliseTelhadoResult(
        id=telhado_id,
        lat=lat,
        lon=lon,
        area_total_m2=area_total_m2,
        aguas=aguas_dto,
        imagem_url=imagem_url,
        imagem_base64=imagem_base64,
        processado_em=processado_em,
        fonte_lidar=lidar_source.name if lidar_source else None,
    )
    await set_cached_result(lat, lon, result)
    return result
