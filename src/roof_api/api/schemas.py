"""Pydantic request/response schemas for telhado API."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AnalisarTelhadoRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude WGS84")
    lon: float = Field(..., ge=-180, le=180, description="Longitude WGS84")


class AguaOut(BaseModel):
    id: UUID
    area_real_m2: float
    inclinacao_graus: float
    orientacao_azimute: float
    geometria_wkt: str

    class Config:
        from_attributes = True


class AnalisarTelhadoResponse(BaseModel):
    id: UUID
    lat: float
    lon: float
    area_total_m2: float
    aguas: list[AguaOut]
    imagem_url: str | None = None
    imagem_base64: str | None = None
    processado_em: datetime
    fonte_lidar: Literal["DGT", "PNOA"] | None = None

    class Config:
        from_attributes = True
