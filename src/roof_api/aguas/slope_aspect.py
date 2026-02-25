"""Slope and aspect (degrees) from DSM using gradient."""

import math
from typing import Tuple

import numpy as np


def slope_aspect_from_dsm(dsm: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    dsm: 2D elevation (meters). Returns (slope_deg, aspect_deg).
    aspect: 0=N, 90=E, 180=S, 270=W (azimuth).
    """
    gx = np.gradient(dsm, axis=1)
    gy = np.gradient(dsm, axis=0)
    slope_rad = np.arctan(np.sqrt(gx**2 + gy**2))
    slope_deg = np.degrees(slope_rad)
    aspect_rad = np.arctan2(-gx, gy)
    aspect_deg = np.degrees(aspect_rad)
    aspect_deg = (aspect_deg + 360) % 360
    return slope_deg.astype(np.float32), aspect_deg.astype(np.float32)
