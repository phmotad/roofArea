"""
Junta Inria (images/ + masks/) e RoofSat (img_color + building_masks) num único
dataset binário para pré-treino: mais exemplos de "telhado vs fundo".

Uso (na raiz do projeto):
  python -m scripts.merge_inria_roofsat_binary --output dados_binario_inria_roofsat
  Treino: use o notebook kaggle_train_roof_deeplabv3.ipynb (pré-treino binário com roof/chips).
"""

import argparse
import shutil
from pathlib import Path

_root = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Unir Inria + RoofSat (imagens + máscaras binárias) numa pasta.")
    parser.add_argument(
        "--output",
        type=str,
        default="./dados_binario_inria_roofsat",
        help="Pasta de saída (images/ + masks/).",
    )
    parser.add_argument(
        "--inria",
        type=str,
        default=None,
        help="Pasta Inria (default: dados_inria com images/ e masks/).",
    )
    parser.add_argument(
        "--roofsat",
        type=str,
        default=None,
        help="Pasta RoofSat (default: dados_inria/Roofsat com img_color e building_masks).",
    )
    args = parser.parse_args()

    inria_base = Path(args.inria) if args.inria else _root / "dados_inria"
    roofsat_base = Path(args.roofsat) if args.roofsat else _root / "dados_inria" / "Roofsat"
    out = Path(args.output)
    images_dir = out / "images"
    masks_dir = out / "masks"
    images_dir.mkdir(parents=True, exist_ok=True)
    masks_dir.mkdir(parents=True, exist_ok=True)

    n = 0
    inria_img = inria_base / "images"
    inria_msk = inria_base / "masks"
    if inria_img.is_dir() and inria_msk.is_dir():
        for f in inria_img.iterdir():
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif"):
                stem = f.stem
                m = inria_msk / f"{stem}.png"
                if not m.exists():
                    m = inria_msk / f"{stem}.tif"
                if m.exists():
                    shutil.copy2(f, images_dir / f.name)
                    shutil.copy2(m, masks_dir / f"{stem}.png" if m.suffix.lower() != ".png" else m.name)
                    n += 1
        print("Inria: copiados", n, "pares.")

    roofsat_img = roofsat_base / "img_color"
    if not roofsat_img.is_dir():
        roofsat_img = roofsat_base / "img"
    roofsat_msk = roofsat_base / "building_masks"
    if roofsat_img.is_dir() and roofsat_msk.is_dir():
        roofsat_n = 0
        for f in roofsat_img.iterdir():
            if f.suffix.lower() in (".png", ".jpg", ".jpeg"):
                stem = f.stem
                m = roofsat_msk / f"{stem}.png"
                if not m.exists():
                    m = roofsat_msk / f"{stem}.tif"
                if m.exists():
                    out_name = f"roofsat_{stem}.png"
                    shutil.copy2(f, images_dir / out_name)
                    shutil.copy2(m, masks_dir / out_name)
                    roofsat_n += 1
        print("RoofSat: copiados", roofsat_n, "pares.")
        n += roofsat_n

    print("Total:", n, "pares em", out.resolve())
    if n:
        print("Pré-treino binário: use notebook kaggle_train_roof_deeplabv3.ipynb com roof/chips (data_dir=", out, ")")


if __name__ == "__main__":
    main()
