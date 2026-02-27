"""
Gera os zips prontos para subir como datasets no Kaggle.

Requer na raiz do projeto:
  - dados_inria/images/ e dados_inria/masks/ (patches Inria)
  - chips_multiclass/images/ e chips_multiclass/masks/
  - dados_inria/Roofsat/ (opcional)

Uso (na raiz do projeto):
  python -m scripts.prepare_kaggle_zips
  python -m scripts.prepare_kaggle_zips --output_dir ./zips_kaggle

Gera:
  - roof-inria-patches.zip   → subir como dataset "roof-inria-patches"
  - roof-chips-multiclass.zip → subir como dataset "roof-chips-multiclass"
  - roof-roofsat.zip         → subir como dataset "roof-roofsat" (opcional)
"""

import argparse
import zipfile
from pathlib import Path

_root = Path(__file__).resolve().parent.parent


def zip_inria(out_dir: Path, dados_inria: Path) -> None:
    images_dir = dados_inria / "images"
    masks_dir = dados_inria / "masks"
    if not images_dir.is_dir() or not masks_dir.is_dir():
        raise FileNotFoundError(
            f"Inria: faltam {images_dir} ou {masks_dir}. "
            "Corra primeiro: python -m scripts.download_inria_dataset --output_dir dados_inria"
        )
    zip_path = out_dir / "roof-inria-patches.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for d, arc_prefix in [(images_dir, "images"), (masks_dir, "masks")]:
            for f in d.iterdir():
                if f.is_file():
                    zf.write(f, arcname=f"{arc_prefix}/{f.name}")
    print("Criado:", zip_path)


def zip_chips(out_dir: Path, chips_dir: Path) -> None:
    if not (chips_dir / "images").is_dir() or not (chips_dir / "masks").is_dir():
        raise FileNotFoundError(
            f"Chips: faltam {chips_dir / 'images'} ou {chips_dir / 'masks'}"
        )
    zip_path = out_dir / "roof-chips-multiclass.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in chips_dir.rglob("*"):
            if f.is_file():
                rel = f.relative_to(chips_dir)
                zf.write(f, arcname=f"chips_multiclass/{rel}".replace("\\", "/"))
    print("Criado:", zip_path)


def zip_roofsat(out_dir: Path, roofsat_dir: Path) -> None:
    if not roofsat_dir.is_dir():
        print("Roofsat não encontrado em", roofsat_dir, "- zip ignorado.")
        return
    zip_path = out_dir / "roof-roofsat.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in roofsat_dir.rglob("*"):
            if f.is_file():
                zf.write(f, arcname=f"Roofsat/{f.relative_to(roofsat_dir)}".replace("\\", "/"))
    print("Criado:", zip_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gerar zips para datasets Kaggle.")
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./zips_kaggle",
        help="Pasta onde guardar os zips.",
    )
    parser.add_argument(
        "--skip_roofsat",
        action="store_true",
        help="Não criar roof-roofsat.zip.",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dados_inria = _root / "dados_inria"
    chips_multiclass = _root / "chips_multiclass"

    zip_inria(out_dir, dados_inria)
    zip_chips(out_dir, chips_multiclass)
    if not args.skip_roofsat:
        zip_roofsat(out_dir, dados_inria / "Roofsat")

    print("\nPróximo passo: em Kaggle → Datasets → New Dataset, faz upload de cada zip.")
    print("Nomes sugeridos: roof-inria-patches, roof-chips-multiclass, roof-roofsat.")


if __name__ == "__main__":
    main()
