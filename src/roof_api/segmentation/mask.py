"""U-Net roof segmentation and morphological post-processing. Binary roof mask."""

import logging
from pathlib import Path

import numpy as np
import cv2
from skimage import morphology

from roof_api.core.config import settings

logger = logging.getLogger(__name__)


def segment_roof_mask(rgb: np.ndarray) -> np.ndarray:
    """
    Input: HxWx3 RGB uint8. Output: HxW bool mask (True = roof).
    Uses U-Net if model exists; else heuristic + morphological cleanup.
    """
    model_path = Path(settings.segmentation_model_path)
    if model_path.exists():
        return _unet_mask(rgb, model_path)
    return _heuristic_mask(rgb)


CLASS_AGUA = 1


def _unet_mask(rgb: np.ndarray, model_path: Path) -> np.ndarray:
    try:
        import torch
        from roof_api.segmentation.unet_model import load_unet, predict
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        num_classes = getattr(settings, "segmentation_num_classes", 1) or 1
        model = load_unet(str(model_path), device, num_classes=num_classes)
        out = predict(model, rgb, device)
        if out.dtype.kind in ("i", "u"):
            mask = (out == CLASS_AGUA).astype(np.uint8)
        else:
            thresh = getattr(settings, "segmentation_prob_threshold", 0.6) if num_classes > 1 else 0.5
            mask = (out > thresh).astype(np.uint8)
        conservative = num_classes > 1
        return _morphological_cleanup(mask, conservative=conservative).astype(bool)
    except Exception as e:
        logger.warning("U-Net inference failed: %s; using heuristic", e)
        return _heuristic_mask(rgb)


def _heuristic_mask(rgb: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = binary > 127
    return _morphological_cleanup(mask.astype(np.uint8), conservative=False).astype(bool)


def _morphological_cleanup(mask: np.ndarray, conservative: bool = False) -> np.ndarray:
    mask = np.asarray(mask, dtype=np.uint8)
    if conservative:
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    else:
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = morphology.remove_small_objects(mask.astype(bool), min_size=50)
    return mask.astype(np.uint8)
