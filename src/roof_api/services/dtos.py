"""Data transfer objects for orchestration result."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class AguaDto:
    id: str
    area_real_m2: float
    inclinacao_graus: float
    orientacao_azimute: float
    geometria_wkt: str


@dataclass
class AnaliseTelhadoResult:
    id: str
    lat: float
    lon: float
    area_total_m2: float
    aguas: list[AguaDto]
    imagem_url: str | None
    imagem_base64: str | None
    processado_em: datetime
    fonte_lidar: str | None
