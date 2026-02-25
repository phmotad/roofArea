"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from roof_api.core.logging import setup_logging
from roof_api.api.routes import telhado_router
from roof_api.api.routes.assets import router as assets_router

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging
    try:
        from roof_api.db import init_db
        await init_db()
    except Exception as e:
        logging.getLogger(__name__).warning("DB init skipped: %s", e)
    yield
    pass


app = FastAPI(
    title="Roof API",
    description="API geoespacial para análise de telhados com LIDAR",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(telhado_router)
app.include_router(assets_router)
