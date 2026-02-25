"""
Extrai N imagens de satélite do Mapbox em redor de um ponto (lat, lon) para anotação no Label Studio.

Gera uma grelha de pontos centrada na região de teste, obtém o bbox de cada (mesmo buffer que a API),
baixa a imagem estática Mapbox 512x512 e grava em PNG com nomes tile_001.png, tile_002.png, ...

Uso (na raiz do projeto):
  python -m scripts.fetch_mapbox_tiles
  python -m scripts.fetch_mapbox_tiles --lat 38.823 --lon -9.163 --count 50 --output_dir ./dados_mapbox
  MAPBOX_ACCESS_TOKEN=xxx python -m scripts.fetch_mapbox_tiles
"""

import argparse
import logging
import sys
from pathlib import Path

import pyproj

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "src"))

from roof_api.core.config import settings
from roof_api.geo.bounds import bounds_from_point

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Coordenadas de teste usadas em test_api.ps1
DEFAULT_LAT = 38.823245206474496
DEFAULT_LON = -9.163455363593444


def fetch_static(minx: float, miny: float, maxx: float, maxy: float, token: str, size: int = 512):
    import io
    import httpx
    from PIL import Image
    bbox = f"{minx},{miny},{maxx},{maxy}"
    url = (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
        f"[{bbox}]/{size}x{size}@2x?access_token={token}"
    )
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        return img


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrair imagens Mapbox em redor de um ponto para Label Studio."
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=DEFAULT_LAT,
        help=f"Latitude do centro da região (default: {DEFAULT_LAT}).",
    )
    parser.add_argument(
        "--lon",
        type=float,
        default=DEFAULT_LON,
        help=f"Longitude do centro da região (default: {DEFAULT_LON}).",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./dados_mapbox",
        help="Pasta onde gravar os PNG (default: ./dados_mapbox).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=50,
        help="Número de imagens a extrair (default: 50). Grelha 5x10.",
    )
    parser.add_argument(
        "--step_m",
        type=float,
        default=55.0,
        help="Distância em metros entre centros de tile (default: 55).",
    )
    args = parser.parse_args()

    token = getattr(settings, "mapbox_access_token", None) or ""
    if not token:
        logger.error("MAPBOX_ACCESS_TOKEN não definido. Configure no .env ou variável de ambiente.")
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    n = max(1, min(args.count, 100))
    cols = 5
    rows = (n + cols - 1) // cols
    if n < cols * rows:
        rows = max(1, (n + cols - 1) // cols)
    geod = pyproj.Geod(ellps="WGS84")
    lat_c, lon_c = args.lat, args.lon
    step = args.step_m
    saved = 0
    idx = 0
    for j in range(rows):
        for i in range(cols):
            if saved >= n:
                break
            off_x = (i - (cols - 1) / 2) * step
            off_y = ((rows - 1) / 2 - j) * step
            clon, clat, _ = geod.fwd(lon_c, lat_c, 90, off_x)
            clon, clat, _ = geod.fwd(clon, clat, 0, off_y)
            minx, miny, maxx, maxy = bounds_from_point(clat, clon)
            try:
                img = fetch_static(minx, miny, maxx, maxy, token)
                idx += 1
                path = out_dir / f"tile_{idx:03d}.png"
                img.save(path)
                saved += 1
                logger.info("Guardado %s (centro %.5f, %.5f)", path.name, clat, clon)
            except Exception as e:
                logger.warning("Falha no tile centro (%.5f, %.5f): %s", clat, clon, e)
    logger.info("Concluído. %d imagens em %s", saved, out_dir.resolve())


if __name__ == "__main__":
    main()
