"""
Converte máscaras 3-class (IDs 0/1/2) para níveis de cinza (0/127/255).

Motivação: facilitar inspeção visual mantendo semântica de classes.
O loader (`RoofDataset`) suporta ambos os formatos quando num_classes==3.

Uso:
  python -m scripts.convert_masks_3class_to_grayscale --masks_dir roof/chips_segmentos/masks_3class
  python -m scripts.convert_masks_3class_to_grayscale --masks_dir roof/chips_segmentos/masks_3class --dry_run
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def _convert_array(arr: np.ndarray) -> np.ndarray:
    """
    Aceita máscara 2D (uint8/int) com valores 0/1/2 ou já em 0/127/255.
    Retorna uint8 com valores 0/127/255.
    """
    if arr.ndim != 2:
        raise ValueError(f"Expected 2D mask, got shape {arr.shape}")
    arr_i = arr.astype(np.int64, copy=False)
    mx = int(arr_i.max()) if arr_i.size else 0
    if mx <= 2:
        out = np.zeros_like(arr_i, dtype=np.uint8)
        out[arr_i == 1] = 127
        out[arr_i >= 2] = 255
        return out
    # Já pode estar em grayscale; normaliza por thresholds.
    out = np.zeros_like(arr_i, dtype=np.uint8)
    out[arr_i >= 64] = 127
    out[arr_i >= 192] = 255
    return out


def convert_dir(masks_dir: Path, dry_run: bool) -> tuple[int, int]:
    masks_dir = Path(masks_dir)
    if not masks_dir.is_dir():
        raise SystemExit(f"masks_dir não existe: {masks_dir}")

    changed = 0
    total = 0
    for p in sorted(masks_dir.glob("*.png")):
        total += 1
        img = Image.open(p)
        if img.mode != "L":
            img = img.convert("L")
        arr = np.array(img)
        out = _convert_array(arr)
        if out.dtype != np.uint8:
            out = out.astype(np.uint8)
        if np.array_equal(out, arr):
            continue
        changed += 1
        if not dry_run:
            Image.fromarray(out, mode="L").save(p)
    return changed, total


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Converter masks_3class 0/1/2 para 0/127/255 (visualmente melhor).")
    parser.add_argument("--masks_dir", type=str, required=True, help="Diretório com PNGs das máscaras 3-class.")
    parser.add_argument("--dry_run", action="store_true", help="Não grava ficheiros; só reporta quantos mudariam.")
    args = parser.parse_args()

    changed, total = convert_dir(Path(args.masks_dir), dry_run=args.dry_run)
    if args.dry_run:
        logger.info("DRY RUN: %d/%d ficheiros seriam convertidos em %s", changed, total, args.masks_dir)
    else:
        logger.info("Convertidos %d/%d ficheiros em %s", changed, total, args.masks_dir)


if __name__ == "__main__":
    main()

