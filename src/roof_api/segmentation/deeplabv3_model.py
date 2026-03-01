"""DeepLabV3+ (torchvision) para segmentação de telhados. Interface compatível com unet_model."""

from pathlib import Path
from typing import Literal

import numpy as np
import torch
import torch.nn as nn


def _get_deeplab_builder(backbone: str):
    try:
        from torchvision.models.segmentation import (
            deeplabv3_resnet50,
            deeplabv3_resnet101,
            deeplabv3_mobilenet_v3_large,
        )
    except ImportError as e:
        raise ImportError("DeepLabV3+ requer torchvision. Instale: pip install torchvision") from e
    m = {
        "resnet50": deeplabv3_resnet50,
        "resnet101": deeplabv3_resnet101,
        "mobilenet_v3_large": deeplabv3_mobilenet_v3_large,
    }
    if backbone not in m:
        backbone = "resnet50"
    return m[backbone]


def load_deeplabv3(
    path: str | Path | None,
    device: torch.device,
    num_classes: int = 1,
    backbone: Literal["resnet50", "resnet101", "mobilenet_v3_large"] = "resnet50",
) -> nn.Module:
    """
    Carrega DeepLabV3+ (torchvision). Se path for ficheiro, carrega state_dict (modelo treinado).
    Caso contrário, instancia o modelo com num_classes (e backbone) para treino ou teste sem checkpoint.
    """
    builder = _get_deeplab_builder(backbone)
    model = builder(num_classes=num_classes, weights=None, weights_backbone=None)
    path = Path(path) if path else None
    if path and path.is_file():
        state = torch.load(path, map_location=device, weights_only=True)
        if isinstance(state, dict) and "model" in state:
            model.load_state_dict(state["model"], strict=False)
        elif isinstance(state, dict) and "state_dict" in state:
            model.load_state_dict(state["state_dict"], strict=False)
        else:
            model.load_state_dict(state, strict=False)
    model.to(device)
    model.eval()
    return model


def _forward_logits(model: nn.Module, x: torch.Tensor) -> torch.Tensor:
    out = model(x)
    if isinstance(out, dict):
        return out["out"]
    return out


def _ensure_size(logits: np.ndarray, h: int, w: int, num_ch: int) -> np.ndarray:
    import cv2
    if logits.ndim == 2:
        if logits.shape[0] != h or logits.shape[1] != w:
            logits = cv2.resize(logits, (w, h), interpolation=cv2.INTER_LINEAR)
        return logits.astype(np.float32)
    if logits.shape[1] != h or logits.shape[2] != w:
        logits = np.stack([
            cv2.resize(logits[i], (w, h), interpolation=cv2.INTER_LINEAR)
            for i in range(logits.shape[0])
        ], axis=0)
    return logits.astype(np.float32)


def predict(model: nn.Module, rgb: np.ndarray, device: torch.device) -> np.ndarray:
    """
    rgb HxWx3 uint8 -> logits HxW (1 canal) ou prob classe 1 (multiclasse). float32.
    """
    import cv2
    x = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255.0).unsqueeze(0).to(device)
    with torch.no_grad():
        out = _forward_logits(model, x)
    out_np = out.cpu().numpy().squeeze(0)
    h, w = rgb.shape[0], rgb.shape[1]
    out_np = _ensure_size(out_np, h, w, out_np.shape[0] if out_np.ndim > 2 else 1)
    if out_np.ndim == 3:
        exp = np.exp(out_np - out_np.max(axis=0, keepdims=True))
        probs = exp / exp.sum(axis=0, keepdims=True)
        return probs[1].astype(np.float32)
    return out_np.astype(np.float32)


def predict_roof_prob(model: nn.Module, rgb: np.ndarray, device: torch.device) -> np.ndarray:
    """HxW float32: probabilidade de pixel ser telhado (1 - prob fundo)."""
    import cv2
    x = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255.0).unsqueeze(0).to(device)
    with torch.no_grad():
        out = _forward_logits(model, x)
    out_np = out.cpu().numpy().squeeze(0)
    h, w = rgb.shape[0], rgb.shape[1]
    out_np = _ensure_size(out_np, h, w, out_np.shape[0] if out_np.ndim > 2 else 1)
    if out_np.ndim == 2:
        logits = out_np.astype(np.float32)
        return (1.0 / (1.0 + np.exp(-np.clip(logits, -20, 20)))).astype(np.float32)
    exp = np.exp(out_np - out_np.max(axis=0, keepdims=True))
    probs = exp / exp.sum(axis=0, keepdims=True)
    return (1.0 - probs[0]).astype(np.float32)


def predict_multiclass_probs(model: nn.Module, rgb: np.ndarray, device: torch.device) -> np.ndarray | None:
    """Multiclasse: HxWxC float32. None se modelo for 1 canal."""
    import cv2
    x = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255.0).unsqueeze(0).to(device)
    with torch.no_grad():
        out = _forward_logits(model, x)
    out_np = out.cpu().numpy().squeeze(0)
    if out_np.ndim == 2:
        return None
    h, w = rgb.shape[0], rgb.shape[1]
    out_np = _ensure_size(out_np, h, w, out_np.shape[0])
    exp = np.exp(out_np - out_np.max(axis=0, keepdims=True))
    probs = exp / exp.sum(axis=0, keepdims=True)
    return probs.astype(np.float32)
