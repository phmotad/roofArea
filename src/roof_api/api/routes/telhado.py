"""Telhado routes: POST /telhado/analisar, GET /telhados/{id}/imagem.png."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from roof_api.api.schemas import (
    AnalisarTelhadoRequest,
    AnalisarTelhadoResponse,
    AguaOut,
)
from roof_api.core.config import settings
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telhado", tags=["telhado"])


@router.post(
    "/analisar",
    response_model=AnalisarTelhadoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def analisar_telhado(
    body: AnalisarTelhadoRequest,
) -> AnalisarTelhadoResponse:
    """Analyse roof at given coordinates: mask, 3D area, waters, image."""
    from roof_api.services.orchestrator import analyse_roof

    try:
        result = await analyse_roof(lat=body.lat, lon=body.lon)
    except ValueError as e:
        msg = str(e).lower()
        if "coordenadas inválidas" in msg or "invalid" in msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        if "nenhum telhado" in msg or "sem dados" in msg or "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except ConnectionError as e:
        logger.exception("Service unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço temporariamente indisponível",
        ) from e

    aguas_out = [
        AguaOut(
            id=UUID(a.id),
            area_real_m2=a.area_real_m2,
            inclinacao_graus=a.inclinacao_graus,
            orientacao_azimute=a.orientacao_azimute,
            geometria_wkt=a.geometria_wkt,
        )
        for a in result.aguas
    ]
    return AnalisarTelhadoResponse(
        id=UUID(result.id),
        lat=result.lat,
        lon=result.lon,
        area_total_m2=result.area_total_m2,
        aguas=aguas_out,
        imagem_url=result.imagem_url,
        imagem_base64=result.imagem_base64 if settings.output_image_base64 else None,
        processado_em=result.processado_em,
        fonte_lidar=result.fonte_lidar.upper() if result.fonte_lidar else None,
    )


