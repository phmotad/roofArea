"""
Descarrega e converte o dataset RoofSense para o formato do Roof API (RGB + máscara binária).

O RoofSense tem 8 classes de material; convertemos para binário: qualquer material de telhado = 255, fundo = 0.
Uso: pré-treino (roof/chips) ou dados extra. Requer: pip install huggingface_hub (ou pip install -e .[data]).

Uso:
  # Tentar download do HuggingFace (se o dataset estiver disponível)
  python -m scripts.download_roofsense_dataset --output roof/chips_roofsense

  # Converter pasta local (gerada pelo RoofSense main.py)
  python -m scripts.download_roofsense_dataset --input_dir "C:\Users\USER\.roofsense\2024.02.28" --output roof/chips_roofsense
"""

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOF_SENSE_HF_REPO = "DimitrisMantas/RoofSense"


def _ensure_rgb(img_path: Path):
    """Load image; if multi-band (e.g. 7 channels), return first 3 as RGB."""
    import numpy as np
    try:
        import rasterio
        with rasterio.open(img_path) as src:
            data = src.read()
        if data.shape[0] >= 3:
            rgb = np.transpose(data[:3], (1, 2, 0))
        else:
            rgb = np.stack([data[0]] * 3, axis=-1)
        return np.asarray(rgb, dtype=np.uint8)
    except Exception:
        pass
    try:
        from PIL import Image
        img = Image.open(img_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return np.asarray(img, dtype=np.uint8)
    except Exception as e:
        logger.warning("Cannot load %s: %s", img_path, e)
        return None


def _mask_to_binary(mask_path: Path) -> "np.ndarray | None":
    """Load raster mask; any pixel > 0 -> 255 (roof), else 0 (background)."""
    import numpy as np
    try:
        import rasterio
        with rasterio.open(mask_path) as src:
            data = src.read(1)
        binary = (data > 0).astype(np.uint8) * 255
        return binary
    except Exception:
        pass
    try:
        from PIL import Image
        img = Image.open(mask_path)
        arr = np.array(img)
        if arr.ndim > 2:
            arr = arr[:, :, 0]
        binary = (arr > 0).astype(np.uint8) * 255
        return binary
    except Exception as e:
        logger.warning("Cannot load mask %s: %s", mask_path, e)
        return None


def convert_local(input_dir: Path, output_dir: Path) -> int:
    """Convert RoofSense folder (images/ + masks/) to our format (binary roof mask, RGB)."""
    import numpy as np
    import cv2

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    images_in = input_dir / "images"
    masks_in = input_dir / "masks"
    if not masks_in.is_dir():
        masks_in = input_dir / "dataset"
        if masks_in.is_dir():
            logger.info("No masks/ found; dataset/ may contain different structure.")
    if not images_in.is_dir():
        images_in = input_dir / "chips"
    if not images_in.is_dir() or not masks_in.is_dir():
        logger.error("Expected images/ (or chips/) and masks/ under %s", input_dir)
        return 0

    out_images = output_dir / "images"
    out_masks = output_dir / "masks"
    out_images.mkdir(parents=True, exist_ok=True)
    out_masks.mkdir(parents=True, exist_ok=True)

    count = 0
    for mask_path in sorted(masks_in.glob("*.tif"))[:]:
        stem = mask_path.stem
        img_path = images_in / f"{stem}.tif"
        if not img_path.exists():
            img_path = images_in / f"{stem}.png"
        if not img_path.exists():
            continue
        rgb = _ensure_rgb(img_path)
        binary = _mask_to_binary(mask_path)
        if rgb is None or binary is None:
            continue
        if rgb.shape[:2] != binary.shape[:2]:
            binary = cv2.resize(binary, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST)
        cv2.imwrite(str(out_images / f"{stem}.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(out_masks / f"{stem}.png"), binary)
        count += 1
    return count


def download_from_hf(output_dir: Path) -> "tuple[Path | None, str]":
    """Download RoofSense repo from HuggingFace. Returns (local_path, error_message)."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        return None, "pip install huggingface_hub"

    try:
        local = snapshot_download(ROOF_SENSE_HF_REPO, repo_type="dataset", local_dir=str(output_dir / "roofsense_raw"))
        return Path(local), ""
    except Exception as e:
        return None, str(e)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download/convert RoofSense to Roof API format (RGB + binary mask).")
    parser.add_argument("--output", type=str, default="roof/chips_roofsense", help="Output dir (images/ + masks/)")
    parser.add_argument("--input_dir", type=str, default=None, help="Local RoofSense folder (e.g. from their main.py)")
    parser.add_argument("--from_hf", action="store_true", help="Try download from HuggingFace first")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    output_dir = root / args.output

    if args.input_dir:
        n = convert_local(Path(args.input_dir), output_dir)
        logger.info("Converted %d pairs to %s", n, output_dir)
        return

    if args.from_hf:
        path, err = download_from_hf(output_dir)
        if err:
            logger.warning("HuggingFace download failed: %s", err)
        if path and path.is_dir():
            n = convert_local(path, output_dir)
            logger.info("Converted %d pairs to %s", n, output_dir)
        return

    logger.info(
        "Use --input_dir <path> to convert a local RoofSense folder, or --from_hf to try HuggingFace. "
        "See docs/roofsense-integracao.md."
    )


if __name__ == "__main__":
    main()
