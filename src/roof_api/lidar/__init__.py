"""LIDAR/DSM: fetch and clip DSM raster; fallback when unavailable."""

from roof_api.lidar.dsm import get_dsm_for_bounds, LidarSource

__all__ = ["get_dsm_for_bounds", "LidarSource"]
