"""
Descarrega o dataset Inria Aerial Image Labeling (segmentação de edifícios)
e converte para o formato do projeto (images/ + masks/ com patches 512x512).

Uso (na raiz do projeto):
  pip install huggingface_hub
  python -m scripts.download_inria_dataset
  python -m scripts.download_inria_dataset --output_dir ./dados_inria --max_images 50

Depois, para treino binário (pré-treino):
  python -m scripts.train_unet --data_dir ./dados_inria --output ./models/unet_roof_pretrain.pt --num_classes 1 --epochs 30

Ou combinar com os teus chips: copiar dados_inria para chips_completo e depois treinar multiclasse
com os teus 11 chips (que têm águas, claraboia, etc.) - o Inria dá milhares de exemplos de "água".
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
from PIL import Image

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

PATCH_SIZE = 512
INRIA_REPO = "blanchon/INRIA-Aerial-Image-Labeling"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarregar Inria Aerial e converter para patches 512x512."
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./dados_inria",
        help="Pasta de saída (images/ + masks/).",
    )
    parser.add_argument(
        "--max_images",
        type=int,
        default=None,
        help="Máximo de imagens train a processar (default: todas).",
    )
    parser.add_argument(
        "--max_patches_per_image",
        type=int,
        default=36,
        help="Máximo de patches por imagem (default: 36, ~6x6 grid).",
    )
    args = parser.parse_args()

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        logger.error("Instale: pip install huggingface_hub")
        sys.exit(1)

    out_dir = Path(args.output_dir)
    images_dir = out_dir / "images"
    masks_dir = out_dir / "masks"
    images_dir.mkdir(parents=True, exist_ok=True)
    masks_dir.mkdir(parents=True, exist_ok=True)

    logger.info("A descarregar %s (apenas train) ...", INRIA_REPO)
    cache = snapshot_download(
        repo_id=INRIA_REPO,
        repo_type="dataset",
        allow_patterns=["data/train/images/*", "data/train/gt/*"],
    )
    cache_path = Path(cache)
    train_img_dir = cache_path / "data" / "train" / "images"
    train_gt_dir = cache_path / "data" / "train" / "gt"
    if not train_img_dir.is_dir():
        train_img_dir = cache_path / "train" / "images"
        train_gt_dir = cache_path / "train" / "gt"
    if not train_img_dir.is_dir():
        logger.error("Estrutura do dataset inesperada em %s", cache_path)
        sys.exit(1)

    tif_images = sorted(train_img_dir.glob("*.tif"))
    if not tif_images:
        tif_images = sorted(train_img_dir.glob("*.png"))
    if args.max_images:
        tif_images = tif_images[: args.max_images]
    logger.info("Encontradas %d imagens train", len(tif_images))

    patch_idx = 0
    for im_path in tif_images:
        stem = im_path.stem
        gt_path = train_gt_dir / (stem + im_path.suffix)
        if not gt_path.exists():
            gt_path = train_gt_dir / f"{stem}.tif"
        if not gt_path.exists():
            logger.warning("Máscara não encontrada para %s", stem)
            continue
        try:
            img = np.array(Image.open(im_path).convert("RGB"))
            gt = np.array(Image.open(gt_path))
        except Exception as e:
            logger.warning("Erro a carregar %s: %s", stem, e)
            continue
        if gt.ndim == 3:
            gt = gt[:, :, 0]
        h, w = img.shape[:2]
        if h < PATCH_SIZE or w < PATCH_SIZE:
            logger.warning("%s demasiado pequena: %dx%d", stem, h, w)
            continue
        n_ph = (h - PATCH_SIZE) // PATCH_SIZE + 1
        n_pw = (w - PATCH_SIZE) // PATCH_SIZE + 1
        count = 0
        for py in range(n_ph):
            for px in range(n_pw):
                if count >= args.max_patches_per_image:
                    break
                y0, x0 = py * PATCH_SIZE, px * PATCH_SIZE
                patch_img = img[y0 : y0 + PATCH_SIZE, x0 : x0 + PATCH_SIZE]
                patch_gt = gt[y0 : y0 + PATCH_SIZE, x0 : x0 + PATCH_SIZE]
                building_ratio = (patch_gt > 127).mean()
                if building_ratio < 0.005:
                    continue
                mask_u8 = np.where(patch_gt > 127, 255, 0).astype(np.uint8)
                out_name = f"inria_{patch_idx:06d}"
                Image.fromarray(patch_img).save(images_dir / f"{out_name}.png")
                Image.fromarray(mask_u8).save(masks_dir / f"{out_name}.png")
                patch_idx += 1
                count += 1
            if count >= args.max_patches_per_image:
                break
    logger.info("Concluído. %d patches em %s", patch_idx, out_dir.resolve())
    logger.info("Treino binário: python -m scripts.train_unet --data_dir %s --output ./models/unet_pretrain.pt --num_classes 1 --epochs 30", out_dir)


if __name__ == "__main__":
    main()
