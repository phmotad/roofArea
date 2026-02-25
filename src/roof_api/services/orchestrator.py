"""Orchestrate full pipeline: ortho -> segment -> DSM -> waters -> persist -> image."""

import base64
import logging
from uuid import uuid4
from datetime import datetime, timezone

import numpy as np
from shapely.geometry import Point as ShapelyPoint
from skimage import measure
from geoalchemy2 import WKTElement

from roof_api.services.dtos import AnaliseTelhadoResult, AguaDto
from roof_api.db.models import Telhado, AguaTelhado
from roof_api.db.session import async_session_factory
from roof_api.core.config import settings
from roof_api.geo import fetch_ortho
from roof_api.lidar import get_dsm_for_bounds, LidarSource
from roof_api.segmentation import segment_roof_mask
from roof_api.aguas import compute_waters
from roof_api.visualization import render_roof_image
from roof_api.services.cache import get_cached_result, set_cached_result
from roof_api.services.image_store import put_image

logger = logging.getLogger(__name__)


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
    dsm, _, lidar_source = get_dsm_for_bounds(minx, miny, maxx, maxy)
    waters_all = compute_waters(mask, dsm, bounds)
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
    if not waters:
        raise ValueError("Nenhum telhado nas coordenadas indicadas")
    area_total_m2 = sum(wa.area_real_m2 for wa in waters)
    if area_total_m2 < min_area_m2:
        raise ValueError("Nenhum telhado nas coordenadas indicadas")
    mask_roof = (labeled == label_at_point).astype(np.uint8)
    png_bytes = render_roof_image(rgb, mask_roof, waters, bounds)

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
