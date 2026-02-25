"""Compute bounding box from lat/lon with buffer in meters."""

import pyproj

from roof_api.core.config import settings


def bounds_from_point(lat: float, lon: float) -> tuple[float, float, float, float]:
    """Return (minx, miny, maxx, maxy) in WGS84 degrees for a square buffer around point."""
    buffer_m = settings.geo_buffer_meters
    geod = pyproj.Geod(ellps="WGS84")
    lon_plus, _, _ = geod.fwd(lon, lat, 90, buffer_m)
    _, lat_plus, _ = geod.fwd(lon, lat, 0, buffer_m)
    lon_minus, _, _ = geod.fwd(lon, lat, -90, buffer_m)
    _, lat_minus, _ = geod.fwd(lon, lat, 180, buffer_m)
    return (lon_minus, lat_minus, lon_plus, lat_plus)
