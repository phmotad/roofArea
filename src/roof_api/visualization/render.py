"""Render PNG: satellite base + 3 camadas (telhado, linhas divisorias, águas) + labels."""

import io
import logging
from typing import List, Tuple

import numpy as np
import cv2
from PIL import Image

from roof_api.aguas.waters import WaterPolygon

logger = logging.getLogger(__name__)

LINES_PROB_THRESHOLD = 0.35


def render_roof_image(
    rgb: np.ndarray,
    mask: np.ndarray,
    waters: List[WaterPolygon],
    bounds: Tuple[float, float, float, float],
    lines_map: np.ndarray | None = None,
    waters_mask: np.ndarray | None = None,
    only_waters: bool = False,
) -> bytes:
    """
    rgb HxWx3, mask HxW (telhados). Desenha 3 camadas separadas (ou só águas se only_waters=True):
    1) Máscara de telhados (modelo 1), 2) Linhas divisorias (modelo 2), 3) Águas (modelo 3 ou polígonos DSM).
    lines_map: HxW float32 prob pixel em linha (opcional). waters_mask: HxW uint8 máscara águas do modelo (opcional).
    waters: polígonos DSM para etiquetas área/inclinação. only_waters: desenhar apenas a camada das águas. Returns PNG bytes.
    """
    h, w = rgb.shape[:2]
    minx, miny, maxx, maxy = bounds
    out = rgb.copy().astype(np.float32)

    if not only_waters:
        mask_u8 = np.asarray(mask, dtype=np.uint8)
        if mask_u8.max() > 1:
            mask_u8 = (mask_u8 > 0).astype(np.uint8)
        mask_3d = np.stack([mask_u8, mask_u8, mask_u8], axis=-1).astype(np.float32) / 255.0
        blend_roof = 0.45
        out = out * (1 - blend_roof * mask_3d) + blend_roof * mask_3d * np.array([255, 120, 80], dtype=np.float32)
        contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out = np.clip(out, 0, 255).astype(np.uint8)
        cv2.drawContours(out, contours, -1, (0, 255, 0), 2)

        if lines_map is not None and lines_map.size > 0 and lines_map.shape[:2] == (h, w):
            line_binary = (lines_map > LINES_PROB_THRESHOLD).astype(np.uint8)
            if line_binary.max() > 0:
                line_3d = np.stack([line_binary, line_binary, line_binary], axis=-1).astype(np.float32)
                blend_line = 0.7
                out = out.astype(np.float32) * (1 - blend_line * line_3d) + blend_line * line_3d * np.array([0, 255, 255], dtype=np.float32)
                out = np.clip(out, 0, 255).astype(np.uint8)

    if only_waters:
        out = np.clip(out, 0, 255).astype(np.uint8)

    if waters_mask is not None and waters_mask.size > 0 and waters_mask.shape[:2] == (h, w):
        wu8 = np.asarray(waters_mask, dtype=np.uint8)
        if wu8.max() > 1:
            wu8 = (wu8 > 0).astype(np.uint8)
        roof_u8 = np.asarray(mask, dtype=np.uint8)
        if roof_u8.max() > 1:
            roof_u8 = (roof_u8 > 0).astype(np.uint8)
        wu8 = np.bitwise_and(wu8, roof_u8)
        if wu8.max() > 0:
            w3d = np.stack([wu8, wu8, wu8], axis=-1).astype(np.float32) / 255.0
            blend_agua = 0.5
            out = out.astype(np.float32) * (1 - blend_agua * w3d) + blend_agua * w3d * np.array([255, 100, 100], dtype=np.float32)
            out = np.clip(out, 0, 255).astype(np.uint8)
            contours_agua, _ = cv2.findContours(wu8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(out, contours_agua, -1, (255, 255, 255), 1)

    colors = [
        (255, 100, 100),
        (100, 255, 100),
        (100, 100, 255),
        (255, 255, 100),
        (255, 100, 255),
    ]
    span_x = max(maxx - minx, 1e-9)
    span_y = max(maxy - miny, 1e-9)

    def _iter_exteriors(geom):
        if geom.is_empty:
            return
        if hasattr(geom, "exterior") and geom.exterior is not None and len(geom.exterior.coords) >= 3:
            yield np.array(geom.exterior.coords, dtype=np.float64)
        elif hasattr(geom, "geoms"):
            for part in geom.geoms:
                yield from _iter_exteriors(part)

    for i, water in enumerate(waters):
        if water.polygon.is_empty or water.polygon.bounds is None:
            continue
        try:
            color = colors[i % len(colors)]
            label = f"{water.area_real_m2:.0f}m² {water.inclinacao_graus:.0f}°"
            cx_sum, cy_sum, n_parts = 0, 0, 0
            for pts in _iter_exteriors(water.polygon):
                if pts.size == 0 or np.any(np.isnan(pts)):
                    continue
                col = (pts[:, 0] - minx) / span_x * (w - 1)
                row = (maxy - pts[:, 1]) / span_y * (h - 1)
                col = np.clip(col, 0, w - 1)
                row = np.clip(row, 0, h - 1)
                pts_px = np.column_stack([col, row]).astype(np.int32)
                if pts_px.shape[0] < 3:
                    continue
                cv2.fillPoly(out, [pts_px], color)
                cv2.polylines(out, [pts_px], True, (255, 255, 255), 1)
                cx_sum += col.mean()
                cy_sum += row.mean()
                n_parts += 1
            if n_parts > 0:
                cy = int(np.clip(cy_sum / n_parts, 0, h - 1))
                cx = int(np.clip(cx_sum / n_parts, 0, w - 1))
                cv2.putText(out, label, (max(0, cx - 40), cy), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        except Exception as e:
            logger.warning("Render water %d failed: %s", i, e)

    pil = Image.fromarray(out)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return buf.getvalue()
