"""
Prepara um dataset para treinar um modelo a prever linhas (wireframes) a partir de imagens.

Usa RoofSat: para cada imagem em img_color/ (ou img/) que tenha gt/<id>.npz, desenha os
segmentos de linha numa máscara binária (mapa de linhas). Resultado: pasta com images/ e
masks/ para treino binário (pixel = linha ou não). Treino: use notebook ou dataset com DeepLabV3+ conforme docs.

Uso (na raiz do projeto):
  python -m scripts.prepare_line_dataset_from_npz --roofsat_dir dados_inria/Roofsat --output line_dataset
  Pipeline usa apenas DeepLabV3+; modelo de linhas separado foi removido.
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

_root = Path(__file__).resolve().parent.parent


def rasterize_lines(lines: np.ndarray, shape_hw: tuple[int, int], thickness: int = 2) -> np.ndarray:
    """Desenha segmentos numa imagem preta. lines: (N, 2, 2) com [[x,y],[x,y]] por segmento."""
    h, w = shape_hw
    out = np.zeros((h, w), dtype=np.uint8)
    for i in range(len(lines)):
        seg = lines[i]
        pt1 = (int(round(seg[0, 0])), int(round(seg[0, 1])))
        pt2 = (int(round(seg[1, 0])), int(round(seg[1, 1])))
        cv2.line(out, pt1, pt2, 255, thickness)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Criar dataset images/ + masks/ (mapa de linhas) a partir de RoofSat + NPZ.")
    parser.add_argument("--roofsat_dir", type=str, default=None, help="Pasta RoofSat (default: dados_inria/Roofsat)")
    parser.add_argument("--output", type=str, default="./line_dataset", help="Pasta de saída (images/ + masks/)")
    parser.add_argument("--line_thickness", type=int, default=2, help="Espessura das linhas na máscara (default: 2)")
    args = parser.parse_args()

    roofsat = Path(args.roofsat_dir) if args.roofsat_dir else _root / "dados_inria" / "Roofsat"
    out_dir = Path(args.output)
    images_out = out_dir / "images"
    masks_out = out_dir / "masks"
    images_out.mkdir(parents=True, exist_ok=True)
    masks_out.mkdir(parents=True, exist_ok=True)

    # Suporta RoofSat (img_color + gt) ou estrutura roof/chips_segmentos (images + gt)
    img_dir = roofsat / "images"
    gt_dir = roofsat / "gt"
    if not img_dir.is_dir() or not gt_dir.is_dir():
        img_dir = roofsat / "img_color"
        if not img_dir.is_dir():
            img_dir = roofsat / "img"
        gt_dir = roofsat / "gt"
    if not img_dir.is_dir() or not gt_dir.is_dir():
        print("Erro: precisamos de images/ e gt/ (ou img_color/ e gt/) em", roofsat)
        return

    try:
        from roof_api.segmentation.dataset import load_roofsat_wireframe
    except ImportError:
        import sys
        sys.path.insert(0, str(_root))
        sys.path.insert(0, str(_root / "src"))
        from roof_api.segmentation.dataset import load_roofsat_wireframe

    count = 0
    for im_path in sorted(img_dir.iterdir()):
        if im_path.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            continue
        stem = im_path.stem
        npz_path = gt_dir / f"{stem}.npz"
        if not npz_path.exists():
            continue
        img = cv2.imread(str(im_path))
        if img is None:
            continue
        h, w = img.shape[:2]
        lines = load_roofsat_wireframe(npz_path)
        if lines is None or len(lines) == 0:
            continue
        line_map = rasterize_lines(lines, (h, w), args.line_thickness)
        out_name = f"{stem}.png"
        cv2.imwrite(str(images_out / out_name), img)
        cv2.imwrite(str(masks_out / out_name), line_map)
        count += 1

    print("Gerados", count, "pares em", out_dir.resolve())
    if count == 0:
        print("Se gt/ não tiver .npz (só .svg), não há nada a processar. O dataset oficial RoofSat inclui .npz.")
    else:
        print("Máscaras em", out_dir, "; pipeline usa apenas DeepLabV3+ (sem modelo de linhas separado).")


if __name__ == "__main__":
    main()
