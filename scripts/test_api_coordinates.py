"""
Testa a API em várias coordenadas e guarda as imagens com máscara.
Uso: python -m scripts.test_api_coordinates [--base_url URL] [--output_dir DIR] [--count N]
"""

import argparse
import sys
from pathlib import Path

import httpx

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))


def main() -> None:
    parser = argparse.ArgumentParser(description="Testa API em múltiplas coordenadas e guarda imagens.")
    parser.add_argument("--base_url", default="http://localhost:8000", help="URL base da API")
    parser.add_argument("--output_dir", default="./test_results", help="Pasta para guardar imagens")
    parser.add_argument("--count", type=int, default=10, help="Número de coordenadas a testar")
    args = parser.parse_args()

    # Coordenadas na zona com cobertura LIDAR DGT (variacoes em redor dos pontos validos)
    coords = [
        (38.823, -9.163),
        (38.815, -9.155),
        (38.812, -9.165),
        (38.825, -9.145),
        (38.811, -9.162),
        (38.828, -9.168),
        (38.813, -9.164),
        (38.810, -9.161),
        (38.824, -9.164),
        (38.816, -9.154),
        (38.829, -9.166),
        (38.809, -9.163),
        (38.826, -9.147),
        (38.818, -9.160),
    ][: args.count]

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/")

    print(f"A testar {len(coords)} coordenadas. Saída: {out_dir.resolve()}")
    for i, (lat, lon) in enumerate(coords, 1):
        try:
            r = httpx.post(
                f"{base}/telhado/analisar",
                json={"lat": lat, "lon": lon},
                timeout=120.0,
            )
            r.raise_for_status()
            data = r.json()
            tid = data["id"]
            area = data["area_total_m2"]
            n_aguas = len(data["aguas"])
            print(f"  {i}. ({lat}, {lon}) -> id={tid[:8]}... area={area:.1f} m², {n_aguas} águas")
            img_r = httpx.get(f"{base}/telhados/{tid}/imagem.png", timeout=60.0)
            img_r.raise_for_status()
            path = out_dir / f"test_{i:02d}_lat{lat:.3f}_lon{lon:.3f}.png"
            path.write_bytes(img_r.content)
            print(f"      Guardado: {path.name}")
        except Exception as e:
            print(f"  {i}. ({lat}, {lon}) -> ERRO: {e}")
    saved = list(out_dir.glob("test_*.png"))
    print(f"\nConcluído. {len(saved)} imagens em {out_dir.resolve()}")


if __name__ == "__main__":
    main()
