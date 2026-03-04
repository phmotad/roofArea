"""
Lista os bounds (lat/lon) que o LIDAR configurado cobre.
Usa LIDAR_DGT_PATH e LIDAR_PNOA_PATH do .env. Útil para saber em que coordenadas há DSM.

Uso:
  python -m scripts.list_lidar_coverage
  python -m scripts.list_lidar_coverage --geojson
  python -m scripts.list_lidar_coverage --check 38.82 -9.16
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Listar cobertura LIDAR (bounds WGS84) ou verificar se um ponto está coberto.")
    parser.add_argument("--geojson", action="store_true", help="Output GeoJSON FeatureCollection de polígonos")
    parser.add_argument("--check", nargs=2, metavar=("LAT", "LON"), help="Verificar se (lat, lon) está coberto")
    args = parser.parse_args()

    from roof_api.lidar import get_lidar_coverage, lidar_covers_point

    coverage = get_lidar_coverage()
    if not coverage:
        print("Nenhum LIDAR configurado ou pastas vazias. Define LIDAR_DGT_PATH e/ou LIDAR_PNOA_PATH no .env")
        return

    if args.check:
        try:
            lat = float(args.check[0])
            lon = float(args.check[1])
        except ValueError:
            print("--check requer lat e lon numéricos")
            sys.exit(1)
        covered = lidar_covers_point(lat, lon)
        print(f"Ponto ({lat}, {lon}): {'COBERTO' if covered else 'SEM LIDAR'}")
        if covered:
            for item in coverage:
                if item["minx"] <= lon <= item["maxx"] and item["miny"] <= lat <= item["maxy"]:
                    print(f"  Ficheiro: {item['path']} (fonte: {item['source']})")
        return

    if args.geojson:
        features = []
        for item in coverage:
            minx, miny, maxx, maxy = item["minx"], item["miny"], item["maxx"], item["maxy"]
            features.append({
                "type": "Feature",
                "properties": {"source": item["source"], "path": item["path"]},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [minx, miny], [maxx, miny], [maxx, maxy], [minx, maxy], [minx, miny]
                    ]],
                },
            })
        print(json.dumps({"type": "FeatureCollection", "features": features}, indent=2))
        return

    print(f"Cobertura LIDAR: {len(coverage)} tile(s)\n")
    for i, item in enumerate(coverage, 1):
        print(f"{i}. {item['source']} | lon [{item['minx']:.6f}, {item['maxx']:.6f}] lat [{item['miny']:.6f}, {item['maxy']:.6f}]")
        print(f"   {item['path']}")


if __name__ == "__main__":
    main()
