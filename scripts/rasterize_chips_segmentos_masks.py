"""
Gera roof/chips_segmentos/masks/ a partir dos .npz em roof/chips_segmentos/gt/.
As imagens em roof/chips_segmentos/images/ definem o tamanho (mesmo nome base).
Assim roof/chips_segmentos fica com images + masks + gt para treinar o modelo de linhas.

Uso:
  python -m scripts.rasterize_chips_segmentos_masks --segmentos_dir roof/chips_segmentos
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

_root = Path(__file__).resolve().parent.parent


def load_wireframe(npz_path: Path) -> np.ndarray:
    """Segmentos de linha do NPZ (chave 'lines'), forma (N, 2, 2)."""
    data = np.load(npz_path, allow_pickle=True)
    return np.asarray(data["lines"], dtype=np.float64)


def rasterize_lines(lines: np.ndarray, shape_hw: tuple[int, int], thickness: int = 2) -> np.ndarray:
    h, w = shape_hw
    out = np.zeros((h, w), dtype=np.uint8)
    for i in range(len(lines)):
        seg = lines[i]
        pt1 = (int(round(seg[0, 0])), int(round(seg[0, 1])))
        pt2 = (int(round(seg[1, 0])), int(round(seg[1, 1])))
        cv2.line(out, pt1, pt2, 255, thickness)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--segmentos_dir", type=str, default=None, help="Pasta chips_segmentos (default: roof/chips_segmentos)")
    parser.add_argument("--line_thickness", type=int, default=2)
    args = parser.parse_args()
    seg_dir = Path(args.segmentos_dir) if args.segmentos_dir else _root / "roof" / "chips_segmentos"
    gt_dir = seg_dir / "gt"
    img_dir = seg_dir / "images"
    masks_dir = seg_dir / "masks"
    if not gt_dir.is_dir() or not img_dir.is_dir():
        print("Precisamos de", gt_dir, "e", img_dir)
        return
    masks_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for npz_path in sorted(gt_dir.glob("*.npz")):
        stem = npz_path.stem
        im_path = img_dir / f"{stem}.png"
        if not im_path.exists():
            im_path = img_dir / f"{stem}.jpg"
        if not im_path.exists():
            continue
        img = cv2.imread(str(im_path))
        if img is None:
            continue
        h, w = img.shape[:2]
        lines = load_wireframe(npz_path)
        if lines is None or len(lines) == 0:
            continue
        line_map = rasterize_lines(lines, (h, w), args.line_thickness)
        cv2.imwrite(str(masks_dir / f"{stem}.png"), line_map)
        n += 1
    print("Máscaras de linhas geradas:", n, "em", masks_dir)


if __name__ == "__main__":
    main()
