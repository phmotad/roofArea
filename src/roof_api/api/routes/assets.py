"""Serve generated assets: GET /telhados/{id}/imagem.png."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from roof_api.services.image_store import get_image

router = APIRouter(tags=["assets"])


@router.get("/telhados/{telhado_id}/imagem.png", response_class=Response)
async def get_telhado_imagem(telhado_id: str) -> Response:
    """Serve PNG image for a roof analysis result."""
    png = get_image(telhado_id)
    if png is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imagem não encontrada")
    return Response(content=png, media_type="image/png")
