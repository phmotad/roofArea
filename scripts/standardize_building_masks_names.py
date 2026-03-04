"""
Padroniza os nomes das máscaras em roof/chips_segmentos/building_masks para
o mesmo esquema das imagens: segmentos_000000.png, segmentos_000001.png, ...

Assumindo correspondência 1:1 por ordem lexicográfica: primeiro building_mask
(sort) -> segmentos_000000.png, segundo -> segmentos_000001.png, etc.
As imagens em chips_segmentos/images já são segmentos_000000 ... segmentos_000549;
o script alinha building_masks a essa numeração.

Uso:
  python -m scripts.standardize_building_masks_names
  python -m scripts.standardize_building_masks_names --output masks_3class
  python -m scripts.standardize_building_masks_names --dry_run
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

_root = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copiar building_masks para nomes segmentos_XXXXXX.png alinhados às imagens."
    )
    parser.add_argument(
        "--segmentos_dir",
        type=Path,
        default=_root / "roof" / "chips_segmentos",
        help="Pasta chips_segmentos (default: roof/chips_segmentos)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="building_masks_renamed",
        help="Subpasta de saída (default: building_masks_renamed). Use masks_3class para sobrescrever as máscaras 3-class.",
    )
    parser.add_argument("--dry_run", action="store_true", help="Só listar o que seria feito.")
    args = parser.parse_args()

    seg_dir = Path(args.segmentos_dir)
    building_dir = seg_dir / "building_masks"
    out_dir = seg_dir / args.output
    images_dir = seg_dir / "images"

    if not building_dir.is_dir():
        print("Não encontrado:", building_dir)
        return

    # Ordem das imagens em chips_segmentos (segmentos_000000, 000001, ...)
    image_files = sorted(images_dir.glob("segmentos_*.png"))
    if not image_files:
        print("Nenhuma imagem segmentos_*.png em", images_dir)
        return

    # Ordem das building_masks (0100.png, 0101.png, ...)
    mask_files = sorted(building_dir.glob("*.png"))
    if not mask_files:
        print("Nenhum PNG em", building_dir)
        return

    if len(mask_files) != len(image_files):
        print(
            "Aviso: building_masks tem",
            len(mask_files),
            "ficheiros, images tem",
            len(image_files),
            "- será usado o mínimo dos dois.",
        )
    n = min(len(mask_files), len(image_files))

    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    for i in range(n):
        src = mask_files[i]
        stem = image_files[i].stem  # segmentos_000000
        dst = out_dir / f"{stem}.png"
        if args.dry_run:
            print(src.name, "->", dst.name)
        else:
            shutil.copy2(src, dst)

    print("Copiados", n, "ficheiros para", out_dir.resolve())
    if args.output == "building_masks_renamed":
        print("Para usar no treino com images/, use masks_dir =", out_dir)


if __name__ == "__main__":
    main()
