"""API route modules."""

from roof_api.api.routes.telhado import router as telhado_router
from roof_api.api.routes.assets import router as assets_router
from roof_api.api.routes.lidar import router as lidar_router

__all__ = ["telhado_router", "assets_router", "lidar_router"]
