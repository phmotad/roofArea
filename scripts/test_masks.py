"""
Testar pipeline de máscara + águas localmente (sem Docker).
Imagem original com as águas do telhado onde (lat, lon) bate.

Uso (na raiz do projeto, .venv ativo):
  python scripts/test_masks.py
  python scripts/test_masks.py --lat 38.82 --lon -9.16
  python scripts/test_masks.py imagem.png
  python scripts/test_masks.py imagem.png --lat 0.5 --lon 0.5

Sem imagem: obtém ortofetada em (lat, lon) e usa esse ponto.
Com imagem: bounds fictícios (0,0,1,1); ponto central (0.5, 0.5) ou --lat/--lon em 0-1.
Guarda: test_mask_overlay.png (original + águas do telhado selecionado).
"""
from pathlib import Path
import sys
import math
import argparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    import numpy as np
    import cv2
    from shapely.geometry import Point as ShapelyPoint
    from skimage import measure

    from roof_api.core.config import settings
    from roof_api.segmentation import segment_roof_mask, segment_lines_map, segment_waters_mask
    from roof_api.aguas import compute_waters
    from roof_api.visualization import render_roof_image

    parser = argparse.ArgumentParser(description="Testar máscara + águas (telhado no ponto)")
    parser.add_argument("imagem", nargs="?", help="PNG opcional; sem ela, obtém ortofetada em (lat,lon)")
    parser.add_argument("--lat", type=float, default=None, help="Latitude (graus) ou, com imagem, fracção 0-1 do centro Y")
    parser.add_argument("--lon", type=float, default=None, help="Longitude (graus) ou, com imagem, fracção 0-1 do centro X")
    args = parser.parse_args()

    lat_default, lon_default = 38.823245, -9.163455
    if args.imagem:
        img_path = Path(args.imagem)
        if not img_path.is_file():
            print("Ficheiro não encontrado:", img_path)
            sys.exit(1)
        rgb = cv2.imread(str(img_path))
        if rgb is None:
            print("Não foi possível ler a imagem:", img_path)
            sys.exit(1)
        rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
        bounds = (0.0, 0.0, 1.0, 1.0)
        lat = args.lat if args.lat is not None else 0.5
        lon = args.lon if args.lon is not None else 0.5
        print("Imagem de ficheiro; ponto (lon, lat) =", lon, lat)
    else:
        from roof_api.geo import fetch_ortho
        lat = args.lat if args.lat is not None else lat_default
        lon = args.lon if args.lon is not None else lon_default
        print("A obter ortofetada em lat=%s lon=%s..." % (lat, lon))
        rgb, bounds = fetch_ortho(lat, lon)
        if rgb is None or rgb.size == 0:
            print("Falha a obter ortofetada. Define MAPBOX_ACCESS_TOKEN no .env")
            sys.exit(1)
        print("Bounds:", bounds)

    minx, miny, maxx, maxy = bounds
    h, w = rgb.shape[:2]
    pt = ShapelyPoint(lon, lat)

    model_path = Path(settings.segmentation_model_path).resolve()
    print("Modelo (DeepLabV3+):", "SIM" if model_path.is_file() else "NÃO (falta .pt)")

    mask = segment_roof_mask(rgb)
    lines_map = segment_lines_map(rgb)
    waters_mask = segment_waters_mask(rgb)

    if not args.imagem:
        from roof_api.lidar import get_dsm_for_bounds
        dsm, _, _ = get_dsm_for_bounds(minx, miny, maxx, maxy)
    else:
        dsm = None

    waters_all = compute_waters(mask, dsm, bounds, lines_map=lines_map)
    min_area_m2 = getattr(settings, "min_roof_area_m2", 10.0)
    labeled = measure.label(np.asarray(mask, dtype=np.uint8), connectivity=2)

    waters_containing = [
        wa for wa in waters_all
        if not wa.polygon.is_empty and wa.polygon.contains(pt) and wa.area_real_m2 >= min_area_m2
    ]
    if waters_containing:
        label_at_point = waters_containing[0].region_label
    else:
        col = (lon - minx) / (maxx - minx) * (w - 1) if maxx != minx else 0
        row = (maxy - lat) / (maxy - miny) * (h - 1) if maxy != miny else 0
        ri = max(0, min(h - 1, int(round(row))))
        ci = max(0, min(w - 1, int(round(col))))
        label_at_point = int(labeled[ri, ci]) if 0 <= ri < h and 0 <= ci < w else 0
        if label_at_point == 0:
            valid_waters = [wa for wa in waters_all if not wa.polygon.is_empty and wa.area_real_m2 >= min_area_m2]
            if valid_waters:
                nearest = min(valid_waters, key=lambda wa: wa.polygon.distance(pt))
                label_at_point = nearest.region_label

    waters = [wa for wa in waters_all if wa.region_label == label_at_point]
    max_dist_m = getattr(settings, "max_roof_distance_from_point_m", 0.0) or 0.0
    if max_dist_m > 0 and waters:
        m_per_deg_lat = 110540.0
        m_per_deg_lon = 111320.0 * math.cos(math.radians(lat))
        waters_near = []
        for wa in waters:
            if wa.polygon.is_empty or wa.polygon.centroid is None:
                continue
            c = wa.polygon.centroid
            dy_m = (lat - c.y) * m_per_deg_lat
            dx_m = (lon - c.x) * m_per_deg_lon
            dist_m = (dx_m * dx_m + dy_m * dy_m) ** 0.5
            if dist_m <= max_dist_m:
                waters_near.append(wa)
        if waters_near:
            waters = waters_near

    if not waters:
        print("Nenhum telhado no ponto indicado.")
        sys.exit(1)

    if max_dist_m > 0:
        from roof_api.services.orchestrator import _mask_from_waters
        mask_roof = _mask_from_waters(waters, bounds, h, w)
    else:
        mask_roof = (labeled == label_at_point).astype(np.uint8)

    area_total = sum(wa.area_real_m2 for wa in waters)
    print("Telhado no ponto: %d águas, área total %.1f m²" % (len(waters), area_total))

    only_waters = getattr(settings, "render_only_waters", False)
    png_bytes = render_roof_image(
        rgb, mask_roof, waters, bounds,
        lines_map=lines_map,
        waters_mask=waters_mask,
        only_waters=only_waters,
    )
    out_path = ROOT / "test_mask_overlay.png"
    with open(out_path, "wb") as f:
        f.write(png_bytes)
    print("Guardado: %s" % out_path)
    print("Concluído.")


if __name__ == "__main__":
    main()
