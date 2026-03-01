"""
Lista coordenadas (lat, lon) cobertas pelo LIDAR/DSM em lidar/.
Uso: python -m scripts.coords_covered_by_lidar [--max N]
Imprime uma linha por ponto: "lat,lon" (para o teste usar só pontos com cobertura).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Coordenadas cobertas pelo LIDAR")
    parser.add_argument("--max", type=int, default=12, help="Máximo de pontos a devolver")
    args = parser.parse_args()

    from roof_api.core.config import settings

    lidar_paths = []
    for attr in ("lidar_dgt_path", "lidar_pnoa_path"):
        p = getattr(settings, attr, "") or ""
        if p:
            path = Path(p).resolve()
            if not path.is_absolute() and ROOT:
                path = ROOT / path
            if path.exists():
                lidar_paths.append(path)

    if not lidar_paths:
        return

    try:
        import rasterio
        from rasterio.warp import transform_bounds
    except ImportError:
        return

    ext = (".tif", ".tiff", ".TIF", ".TIFF")
    points = []
    seen = set()

    for base in lidar_paths:
        if base.is_file() and base.suffix in ext:
            files = [base]
        else:
            files = sorted(f for f in base.rglob("*") if f.suffix in ext and f.is_file())
        for f in files:
            if len(points) >= args.max:
                break
            try:
                with rasterio.open(f) as src:
                    rb = src.bounds
                    if src.crs and src.crs.is_geographic:
                        minx, miny, maxx, maxy = rb.left, rb.bottom, rb.right, rb.top
                    else:
                        minx, miny, maxx, maxy = transform_bounds(
                            src.crs, "EPSG:4326", rb.left, rb.bottom, rb.right, rb.top
                        )
                    lat_c = (miny + maxy) / 2.0
                    lon_c = (minx + maxx) / 2.0
                    span_lat = max(maxy - miny, 1e-6)
                    span_lon = max(maxx - minx, 1e-6)
                    for lat, lon in (
                        (lat_c, lon_c),
                        (lat_c + span_lat * 0.25, lon_c),
                        (lat_c, lon_c + span_lon * 0.25),
                    ):
                        key = (round(lat, 6), round(lon, 6))
                        if key not in seen and len(points) < args.max:
                            seen.add(key)
                            points.append((lat, lon))
            except Exception:
                continue
        if len(points) >= args.max:
            break

    for lat, lon in points[: args.max]:
        print(f"{lat},{lon}")


if __name__ == "__main__":
    main()
