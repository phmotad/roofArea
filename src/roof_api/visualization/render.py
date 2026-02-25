"""Render PNG: satellite base, roof mask, waters colored, labels (area, slope)."""

import io
from typing import List, Tuple

import numpy as np
import cv2
from PIL import Image

from roof_api.aguas.waters import WaterPolygon


def render_roof_image(
    rgb: np.ndarray,
    mask: np.ndarray,
    waters: List[WaterPolygon],
    bounds: Tuple[float, float, float, float],
) -> bytes:
    """
    rgb HxWx3, mask HxW. waters with polygon in geo coords - we draw per-pixel by rasterizing.
    Returns PNG bytes.
    """
    h, w = rgb.shape[:2]
    minx, miny, maxx, maxy = bounds
    out = rgb.copy()
    overlay = out.astype(np.float32)
    mask_u8 = np.asarray(mask, dtype=np.uint8)
    if mask_u8.max() > 1:
        mask_u8 = (mask_u8 > 0).astype(np.uint8)
    mask_3d = np.stack([mask_u8, mask_u8, mask_u8], axis=-1).astype(np.float32) / 255.0
    blend = 0.55
    overlay = overlay * (1 - blend * mask_3d) + blend * mask_3d * np.array([255, 120, 80], dtype=np.float32)
    out = np.clip(overlay, 0, 255).astype(np.uint8)
    contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(out, contours, -1, (0, 255, 0), 2)

    colors = [
        (255, 100, 100),
        (100, 255, 100),
        (100, 100, 255),
        (255, 255, 100),
        (255, 100, 255),
    ]
    for i, water in enumerate(waters):
        if water.polygon.is_empty:
            continue
        try:
            poly = water.polygon
            if poly.bounds is None or len(poly.exterior.coords) < 3:
                continue
            xmin, ymin, xmax, ymax = poly.bounds
            pts = np.array(poly.exterior.coords)
            col = (pts[:, 0] - minx) / (maxx - minx) * (w - 1) if maxx != minx else np.zeros_like(pts[:, 0])
            row = (maxy - pts[:, 1]) / (maxy - miny) * (h - 1) if maxy != miny else np.zeros_like(pts[:, 1])
            pts_px = np.column_stack([col, row]).astype(np.int32)
            color = colors[i % len(colors)]
            cv2.fillPoly(out, [pts_px], color)
            cv2.polylines(out, [pts_px], True, (255, 255, 255), 1)
            cy, cx = int(row.mean()), int(col.mean())
            label = f"{water.area_real_m2:.0f}m² {water.inclinacao_graus:.0f}°"
            cv2.putText(out, label, (cx - 40, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        except Exception:
            continue

    pil = Image.fromarray(out)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return buf.getvalue()
