"""U-Net model load and inference for roof segmentation."""

from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn


def load_unet(path: str, device: torch.device, num_classes: int | None = None) -> nn.Module:
    """Load U-Net from checkpoint. Expects state_dict with 'model' or full state_dict.
    If num_classes is None, uses checkpoint key 'num_classes' or defaults to 1 (binary)."""
    state = torch.load(path, map_location=device, weights_only=True)
    if num_classes is None and isinstance(state, dict) and "num_classes" in state:
        num_classes = int(state["num_classes"])
    if num_classes is None:
        num_classes = 1
    out_ch = num_classes
    model = UNet(in_channels=3, out_channels=out_ch)
    if isinstance(state, dict) and "model" in state:
        model.load_state_dict(state["model"], strict=False)
    elif isinstance(state, dict):
        model.load_state_dict(state, strict=False)
    model.to(device)
    model.eval()
    return model


def predict(model: nn.Module, rgb: np.ndarray, device: torch.device) -> np.ndarray:
    """
    rgb HxWx3 uint8 ->
    - 1-channel model: logits HxW float32.
    - Multiclass: probability of class 1 (água) HxW float32, for conservative thresholding and less over-segmentation.
    """
    import cv2
    x = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255.0).unsqueeze(0).to(device)
    with torch.no_grad():
        out = model(x)
    out_channels = out.shape[1]
    if out_channels == 1:
        logits = out.squeeze(1).cpu().numpy()
        if logits.shape != rgb.shape[:2]:
            logits = cv2.resize(
                logits,
                (rgb.shape[1], rgb.shape[0]),
                interpolation=cv2.INTER_LINEAR,
            )
        return logits.astype(np.float32)
    logits_np = out.cpu().numpy().squeeze(0)
    h_in, w_in = rgb.shape[0], rgb.shape[1]
    if logits_np.shape[1] != h_in or logits_np.shape[2] != w_in:
        logits_np = np.stack([
            cv2.resize(logits_np[i], (w_in, h_in), interpolation=cv2.INTER_LINEAR)
            for i in range(logits_np.shape[0])
        ], axis=0)
    exp_logits = np.exp(logits_np - logits_np.max(axis=0, keepdims=True))
    probs = exp_logits / exp_logits.sum(axis=0, keepdims=True)
    prob_agua = probs[1].astype(np.float32)
    return prob_agua


class UNet(nn.Module):
    """Simple U-Net: 3 -> 1 channel, same spatial size with padding."""

    def __init__(self, in_channels: int = 3, out_channels: int = 1):
        super().__init__()
        self.enc1 = self._block(in_channels, 64)
        self.enc2 = self._block(64, 128)
        self.enc3 = self._block(128, 256)
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = self._block(256, 512)
        self.up3 = nn.ConvTranspose2d(512, 256, 2, stride=2)
        self.dec3 = self._block(512, 256)
        self.up2 = nn.ConvTranspose2d(256, 128, 2, stride=2)
        self.dec2 = self._block(256, 128)
        self.up1 = nn.ConvTranspose2d(128, 64, 2, stride=2)
        self.dec1 = self._block(128, 64)
        self.out = nn.Conv2d(64, out_channels, 1)

    @staticmethod
    def _block(in_c: int, out_c: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv2d(in_c, out_c, 3, padding=1),
            nn.BatchNorm2d(out_c),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_c, out_c, 3, padding=1),
            nn.BatchNorm2d(out_c),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        b = self.bottleneck(self.pool(e3))
        d3 = self.dec3(torch.cat([self.up3(b), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return self.out(d1)
