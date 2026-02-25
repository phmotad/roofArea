"""API route modules."""

from roof_api.api.routes.telhado import router as telhado_router
from roof_api.api.routes.assets import router as assets_router

__all__ = ["telhado_router", "assets_router"]
