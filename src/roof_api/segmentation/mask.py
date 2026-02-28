"""Segmentação de telhados: DeepLabV3+ (torchvision) + pós-processamento. Modelo de linhas: U-Net."""

import logging
from pathlib import Path

import numpy as np
import cv2
from skimage import morphology

from roof_api.core.config import settings

logger = logging.getLogger(__name__)

CLASS_AGUA = 1


def segment_roof_mask(rgb: np.ndarray) -> np.ndarray:
    """
    Input: HxWx3 RGB uint8. Output: HxW bool mask (True = roof).
    Usa DeepLabV3+ como único modelo de segmentação principal.
    """
    model_path = Path(settings.segmentation_model_path).resolve()
    if not model_path.is_file():
        logger.warning(
            "Segmentação: modelo não é um ficheiro em %s (path absoluto: %s); a usar máscara heurística.",
            settings.segmentation_model_path,
            model_path,
        )
        return _heuristic_mask(rgb)
    return _segment_mask_deeplabv3(rgb, model_path)


def _segment_mask_deeplabv3(rgb: np.ndarray, model_path: Path) -> np.ndarray:
    try:
        import torch
        from roof_api.segmentation.deeplabv3_model import load_deeplabv3, predict_roof_prob
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        num_classes = getattr(settings, "segmentation_num_classes", 5) or 5
        thresh = getattr(settings, "segmentation_prob_threshold", 0.6) if num_classes > 1 else 0.5
        backbone = getattr(settings, "segmentation_deeplab_backbone", "resnet50") or "resnet50"
        model = load_deeplabv3(str(model_path), device, num_classes=num_classes, backbone=backbone)
        prob_roof = predict_roof_prob(model, rgb, device)
        mask = (prob_roof > thresh).astype(np.uint8)
        conservative = num_classes > 1
        return _morphological_cleanup(mask, conservative=conservative).astype(bool)
    except Exception as e:
        logger.warning("Segmentação DeepLabV3 falhou: %s; a usar heurística", e)
        return _heuristic_mask(rgb)


def _heuristic_mask(rgb: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = binary > 127
    return _morphological_cleanup(mask.astype(np.uint8), conservative=False).astype(bool)


def segment_lines_map(rgb: np.ndarray) -> np.ndarray | None:
    """
    Optional: run U-Net lines model. Returns HxW float32 (prob pixel on line), or None if not configured.
    """
    lines_path = Path(getattr(settings, "segmentation_lines_model_path", "") or "")
    if not lines_path.exists():
        return None
    try:
        import torch
        from roof_api.segmentation.unet_model import load_unet, predict
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = load_unet(str(lines_path), device, num_classes=1)
        logits = predict(model, rgb, device)
        prob = (1.0 / (1.0 + np.exp(-np.clip(logits, -20, 20)))).astype(np.float32)
        return prob
    except Exception as e:
        logger.warning("U-Net lines inference failed: %s; skipping lines", e)
        return None


def segment_waters_mask(rgb: np.ndarray) -> np.ndarray | None:
    """
    Opcional: máscara de águas (classe 1) do modelo DeepLabV3 multiclasse. HxW uint8 (1=água, 0=resto). None se num_classes<=1.
    """
    model_path = Path(settings.segmentation_model_path).resolve()
    num_classes = getattr(settings, "segmentation_num_classes", 5) or 5
    if not model_path.is_file() or num_classes <= 1:
        return None
    try:
        import torch
        from roof_api.segmentation.deeplabv3_model import load_deeplabv3, predict_multiclass_probs
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        backbone = getattr(settings, "segmentation_deeplab_backbone", "resnet50") or "resnet50"
        model = load_deeplabv3(str(model_path), device, num_classes=num_classes, backbone=backbone)
        probs = predict_multiclass_probs(model, rgb, device)
        if probs is None or probs.shape[2] <= CLASS_AGUA:
            return None
        thresh = getattr(settings, "segmentation_prob_threshold", 0.6)
        mask = (probs[:, :, CLASS_AGUA] > thresh).astype(np.uint8)
        return mask
    except Exception as e:
        logger.warning("Segment waters mask failed: %s; skipping", e)
        return None


def _morphological_cleanup(mask: np.ndarray, conservative: bool = False) -> np.ndarray:
    mask = np.asarray(mask, dtype=np.uint8)
    if conservative:
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    else:
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = morphology.remove_small_objects(mask.astype(bool), max_size=49)
    return mask.astype(np.uint8)
