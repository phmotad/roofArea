"""
Cria a estrutura roof/ a partir de dados_inria, Roofsat e chips_multiclass:
  roof/chips/           (images + masks) <- Inria + RoofSat, nomes chip_000001.png
  roof/chips_multiclass/ (images + masks) <- chips_multiclass, nomes multiclass_000001.png
  roof/chips_segmentos/  (images + gt/*.npz) <- RoofSat onde existe .npz, nomes segmentos_000001.png/.npz

Uso (na raiz do projeto):
  python -m scripts.prepare_roof_structure --output roof
  python -m scripts.prepare_roof_structure --inria dados_inria --roofsat dados_inria/Roofsat --chips_multiclass chips_multiclass --output roof
"""

import argparse
import shutil
from pathlib import Path

_root = Path(__file__).resolve().parent.parent


def _copy_pair(im_path: Path, m_path: Path, out_img: Path, out_msk: Path, out_name: str) -> bool:
    """Copia par imagem+máscara. out_name é o nome do ficheiro de saída (ex.: chip_000001.png)."""
    if not m_path.exists():
        return False
    ext = im_path.suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".tif"):
        return False
    out_img = Path(out_img)
    out_msk = Path(out_msk)
    out_img.mkdir(parents=True, exist_ok=True)
    out_msk.mkdir(parents=True, exist_ok=True)
    img_dest = out_img / out_name
    msk_dest = out_msk / (Path(out_name).stem + ".png")
    shutil.copy2(im_path, img_dest)
    shutil.copy2(m_path, msk_dest)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Criar estrutura roof/ com chips, chips_multiclass, chips_segmentos.")
    parser.add_argument("--output", type=str, default="./roof", help="Pasta de saída (ex.: roof)")
    parser.add_argument("--inria", type=str, default=None, help="Pasta Inria com images/ e masks/")
    parser.add_argument("--roofsat", type=str, default=None, help="Pasta RoofSat (img_color, building_masks, gt)")
    parser.add_argument("--chips_multiclass", type=str, default=None, help="Pasta chips_multiclass com images/ e masks/")
    args = parser.parse_args()

    inria_base = Path(args.inria) if args.inria else _root / "dados_inria"
    roofsat_base = Path(args.roofsat) if args.roofsat else _root / "dados_inria" / "Roofsat"
    chips_mc_base = Path(args.chips_multiclass) if args.chips_multiclass else _root / "chips_multiclass"
    out = Path(args.output)

    # --- roof/chips (binário: Inria + RoofSat) ---
    chips_img = out / "chips" / "images"
    chips_msk = out / "chips" / "masks"
    chips_img.mkdir(parents=True, exist_ok=True)
    chips_msk.mkdir(parents=True, exist_ok=True)
    idx = 0
    inria_img = inria_base / "images"
    inria_msk = inria_base / "masks"
    if inria_img.is_dir() and inria_msk.is_dir():
        for f in sorted(inria_img.iterdir()):
            stem = f.stem
            m = inria_msk / f"{stem}.png"
            if not m.exists():
                m = inria_msk / f"{stem}.tif"
            if _copy_pair(f, m, chips_img, chips_msk, f"chip_{idx:06d}.png"):
                idx += 1
    n_chips_inria = idx
    roofsat_img = roofsat_base / "img_color"
    if not roofsat_img.is_dir():
        roofsat_img = roofsat_base / "img"
    roofsat_msk = roofsat_base / "building_masks"
    if roofsat_img.is_dir() and roofsat_msk.is_dir():
        for f in sorted(roofsat_img.iterdir()):
            stem = f.stem
            m = roofsat_msk / f"{stem}.png"
            if not m.exists():
                m = roofsat_msk / f"{stem}.tif"
            if _copy_pair(f, m, chips_img, chips_msk, f"chip_{idx:06d}.png"):
                idx += 1
    print("roof/chips:", idx, "pares (Inria:", n_chips_inria, ", RoofSat:", idx - n_chips_inria, ")")

    # --- roof/chips_multiclass ---
    mc_img = out / "chips_multiclass" / "images"
    mc_msk = out / "chips_multiclass" / "masks"
    mc_img.mkdir(parents=True, exist_ok=True)
    mc_msk.mkdir(parents=True, exist_ok=True)
    idx_mc = 0
    if (chips_mc_base / "images").is_dir() and (chips_mc_base / "masks").is_dir():
        for f in sorted((chips_mc_base / "images").iterdir()):
            stem = f.stem
            m = (chips_mc_base / "masks") / f"{stem}.png"
            if not m.exists():
                m = (chips_mc_base / "masks") / f"{stem}.tif"
            if _copy_pair(f, m, mc_img, mc_msk, f"multiclass_{idx_mc:06d}.png"):
                idx_mc += 1
    print("roof/chips_multiclass:", idx_mc, "pares")

    # --- roof/chips_segmentos (imagens + npz; só onde existe .npz) ---
    seg_img = out / "chips_segmentos" / "images"
    seg_gt = out / "chips_segmentos" / "gt"
    seg_img.mkdir(parents=True, exist_ok=True)
    seg_gt.mkdir(parents=True, exist_ok=True)
    idx_seg = 0
    gt_dir = roofsat_base / "gt"
    if roofsat_img.is_dir() and gt_dir.is_dir():
        for f in sorted(roofsat_img.iterdir()):
            if f.suffix.lower() not in (".png", ".jpg", ".jpeg"):
                continue
            stem = f.stem
            npz = gt_dir / f"{stem}.npz"
            if npz.exists():
                shutil.copy2(f, seg_img / f"segmentos_{idx_seg:06d}.png")
                shutil.copy2(npz, seg_gt / f"segmentos_{idx_seg:06d}.npz")
                idx_seg += 1
    print("roof/chips_segmentos:", idx_seg, "pares (images + npz)")
    if idx_seg == 0:
        print("  (sem .npz em gt/; adiciona ficheiros .npz para treinar o modelo de linhas)")

    print("Estrutura em", out.resolve(), "pronta.")


if __name__ == "__main__":
    main()
