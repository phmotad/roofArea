"""LIDAR/DSM: fetch and clip DSM raster; fallback when unavailable."""

from roof_api.lidar.dsm import (
    get_dsm_for_bounds,
    get_lidar_coverage,
    lidar_covers_point,
    LidarSource,
)

__all__ = ["get_dsm_for_bounds", "get_lidar_coverage", "lidar_covers_point", "LidarSource"]
