"""PyTorch Dataset for roof images + binary or multiclass masks. Same format as inference input."""

import logging
from pathlib import Path

import numpy as np
import torch
import cv2
from PIL import Image
from torch.utils.data import Dataset

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
SUPPORTED_MASK_EXT = {".png", ".tif", ".tiff"}


def discover_pairs(images_dir: Path, masks_dir: Path) -> list[tuple[Path, Path]]:
    """
    Find (image_path, mask_path) where basename matches (without extension).
    Supports PNG/JPG/TIF and also .npy with naming img_K.npy / mask_K.npy (pair by index K).
    """
    images_dir = Path(images_dir)
    masks_dir = Path(masks_dir)
    if not images_dir.is_dir() or not masks_dir.is_dir():
        return []

    pairs: list[tuple[Path, Path]] = []
    for im_path in images_dir.iterdir():
        if im_path.suffix.lower() in (".npy",):
            stem = im_path.stem
            if stem.startswith("img_"):
                try:
                    k = int(stem.split("_")[1])
                    mask_path = masks_dir / f"mask_{k}.npy"
                    if mask_path.exists():
                        pairs.append((im_path, mask_path))
                except (IndexError, ValueError):
                    pass
            continue
        if im_path.suffix.lower() not in SUPPORTED_IMAGE_EXT:
            continue
        stem = im_path.stem
        for ext in SUPPORTED_MASK_EXT:
            mask_path = masks_dir / f"{stem}{ext}"
            if mask_path.exists():
                pairs.append((im_path, mask_path))
                break
        else:
            mask_path = masks_dir / f"{stem}.npy"
            if mask_path.exists():
                pairs.append((im_path, mask_path))
    if pairs:
        pairs.sort(key=lambda p: (p[0].stem, p[1].stem))
    return pairs


class RoofDataset(Dataset):
    """
    Dataset of RGB roof images and masks.
    - num_classes==1: binary masks (0 = background, 1 = roof); y is (1, H, W) float for BCE.
    - num_classes>1: multiclass masks (0=fund, 1=agua, 2=claraboia, 3=divisoria, 4=laje); y is (H, W) long for CrossEntropy.
    Images and masks are resized to (height, width) for training.
    """

    def __init__(
        self,
        images_dir: str | Path,
        masks_dir: str | Path,
        size: tuple[int, int] = (256, 256),
        augment: bool = False,
        num_classes: int = 1,
    ):
        self.images_dir = Path(images_dir)
        self.masks_dir = Path(masks_dir)
        self.size = size
        self.augment = augment
        self.num_classes = max(1, int(num_classes))
        self.pairs = discover_pairs(self.images_dir, self.masks_dir)
        if not self.pairs:
            logger.warning("No image/mask pairs in %s and %s", images_dir, masks_dir)

    def __len__(self) -> int:
        return len(self.pairs)

    def _load_image(self, path: Path) -> np.ndarray:
        if path.suffix.lower() == ".npy":
            arr = np.load(path)
            arr = np.asarray(arr, dtype=np.uint8)
            while arr.ndim > 3:
                arr = arr.squeeze(0)
            if arr.ndim == 2:
                arr = np.stack([arr, arr, arr], axis=-1)
            elif arr.ndim == 3:
                if arr.shape[0] in (1, 3, 4) and arr.shape[1] == arr.shape[2]:
                    arr = np.transpose(arr, (1, 2, 0))
                if arr.shape[-1] == 1:
                    arr = np.repeat(arr, 3, axis=-1)
                elif arr.shape[-1] == 4:
                    arr = arr[..., :3]
            if arr.ndim != 3 or arr.shape[-1] != 3:
                raise ValueError(f"Unexpected npy image shape {arr.shape} in {path}")
            return arr
        img = Image.open(path).convert("RGB")
        return np.array(img, dtype=np.uint8)

    def _load_mask(self, path: Path) -> np.ndarray:
        if path.suffix.lower() == ".npy":
            arr = np.load(path)
            arr = np.asarray(arr, dtype=np.int64)
            if arr.ndim == 3:
                arr = arr.squeeze()
            if self.num_classes > 1:
                arr = np.clip(arr, 0, self.num_classes - 1).astype(np.int64)
                return arr
            return (arr > 0).astype(np.uint8)
        img = Image.open(path)
        if img.mode != "L":
            img = img.convert("L")
        arr = np.array(img, dtype=np.int64)
        if self.num_classes > 1:
            if arr.max() > 10:
                arr = np.round(arr / 51.0).clip(0, self.num_classes - 1).astype(np.int64)
            else:
                arr = np.clip(arr, 0, self.num_classes - 1).astype(np.int64)
            return arr
        return (arr > 127).astype(np.uint8)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        im_path, mask_path = self.pairs[idx]
        rgb = self._load_image(im_path)
        mask = self._load_mask(mask_path)
        h, w = rgb.shape[0], rgb.shape[1]
        if mask.shape[:2] != (h, w):
            mask = cv2.resize(
                mask.astype(np.int64) if self.num_classes > 1 else mask.astype(np.uint8),
                (w, h),
                interpolation=cv2.INTER_NEAREST,
            )
            mask = mask.astype(np.int64) if self.num_classes > 1 else mask.astype(np.uint8)
        if (h, w) != self.size:
            rgb = cv2.resize(rgb, (self.size[1], self.size[0]), interpolation=cv2.INTER_LINEAR)
            mask = cv2.resize(
                mask.astype(np.int64) if self.num_classes > 1 else mask.astype(np.uint8),
                (self.size[1], self.size[0]),
                interpolation=cv2.INTER_NEAREST,
            )
            mask = mask.astype(np.int64) if self.num_classes > 1 else mask.astype(np.uint8)
        if self.augment:
            rgb, mask = _augment(rgb, mask)
        x = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255.0)
        if self.num_classes > 1:
            y = torch.from_numpy(mask).long()
        else:
            y = torch.from_numpy(mask).float().unsqueeze(0)
        return x, y


def _augment(rgb: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Augmentação geométrica e fotométrica (inspirada em pipelines de segmentação
    com poucos dados). Aplica as mesmas transformações geométricas à imagem e à máscara.
    """
    h, w = rgb.shape[:2]
    rng = np.random.default_rng()

    if rng.random() > 0.5:
        rgb = np.ascontiguousarray(rgb[:, ::-1])
        mask = np.ascontiguousarray(mask[:, ::-1])
    if rng.random() > 0.5:
        rgb = np.ascontiguousarray(rgb[::-1])
        mask = np.ascontiguousarray(mask[::-1])

    k = rng.integers(0, 4)
    if k == 1:
        rgb = np.ascontiguousarray(np.rot90(rgb, 1))
        mask = np.ascontiguousarray(np.rot90(mask, 1))
    elif k == 2:
        rgb = np.ascontiguousarray(np.rot90(rgb, 2))
        mask = np.ascontiguousarray(np.rot90(mask, 2))
    elif k == 3:
        rgb = np.ascontiguousarray(np.rot90(rgb, 3))
        mask = np.ascontiguousarray(np.rot90(mask, 3))

    h, w = rgb.shape[0], rgb.shape[1]
    scale = float(rng.uniform(0.85, 1.15))
    if scale != 1.0:
        new_h, new_w = int(round(h * scale)), int(round(w * scale))
        new_h, new_w = max(2, new_h), max(2, new_w)
        rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        mask_dtype = mask.dtype
        mask = cv2.resize(mask.astype(np.uint8), (new_w, new_h), interpolation=cv2.INTER_NEAREST)
        if mask_dtype == np.int64:
            mask = mask.astype(np.int64)
        else:
            mask = mask.astype(np.uint8)
        if scale > 1.0:
            y0 = (new_h - h) // 2
            x0 = (new_w - w) // 2
            rgb = rgb[y0 : y0 + h, x0 : x0 + w]
            mask = mask[y0 : y0 + h, x0 : x0 + w]
        else:
            out_rgb = np.zeros((h, w, 3), dtype=rgb.dtype)
            out_mask = np.zeros((h, w), dtype=mask.dtype)
            y0 = (h - new_h) // 2
            x0 = (w - new_w) // 2
            out_rgb[y0 : y0 + new_h, x0 : x0 + new_w] = rgb
            out_mask[y0 : y0 + new_h, x0 : x0 + new_w] = mask
            rgb, mask = out_rgb, out_mask

    brightness = float(rng.uniform(0.85, 1.15))
    rgb = np.clip(rgb.astype(np.float32) * brightness, 0, 255).astype(np.uint8)

    contrast = float(rng.uniform(0.9, 1.1))
    mean = rgb.astype(np.float32).mean()
    rgb = np.clip((rgb.astype(np.float32) - mean) * contrast + mean, 0, 255).astype(np.uint8)

    angle_deg = float(rng.uniform(-20, 20))
    if abs(angle_deg) >= 0.5:
        h, w = rgb.shape[:2]
        center = (w / 2.0, h / 2.0)
        M = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
        rgb = cv2.warpAffine(rgb, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
        mask_dtype = mask.dtype
        mask = cv2.warpAffine(mask.astype(np.uint8), M, (w, h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        mask = mask.astype(mask_dtype) if mask_dtype != np.uint8 else mask.astype(np.uint8)

    sigma = float(rng.uniform(0, 8))
    if sigma > 0.5:
        noise = rng.normal(0, sigma, size=rgb.shape).astype(np.float32)
        rgb = np.clip(rgb.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    return rgb, mask
