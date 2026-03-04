"""LIDAR: GET /lidar/coverage (bounds) e GET /lidar/covers (verificar ponto)."""

import logging

from fastapi import APIRouter, Query

from roof_api.lidar import get_lidar_coverage, lidar_covers_point

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lidar", tags=["lidar"])


@router.get("/coverage")
async def lidar_coverage() -> list[dict]:
    """
    Lista os bounds (lon/lat WGS84) que o LIDAR configurado cobre.
    Cada item: minx, miny, maxx, maxy (graus), source (DGT|PNOA), path.
    """
    return get_lidar_coverage()


@router.get("/covers")
async def lidar_covers(
    lat: float = Query(..., ge=-90, le=90, description="Latitude WGS84"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude WGS84"),
) -> dict:
    """Indica se o ponto (lat, lon) está coberto por algum DSM LIDAR configurado."""
    covered = lidar_covers_point(lat, lon)
    out: dict = {"lat": lat, "lon": lon, "covers": covered}
    if covered:
        for item in get_lidar_coverage():
            if item["minx"] <= lon <= item["maxx"] and item["miny"] <= lat <= item["maxy"]:
                out["source"] = item["source"]
                out["path"] = item["path"]
                break
    return out
