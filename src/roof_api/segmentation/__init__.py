"""Roof segmentation: U-Net inference + morphological post-processing."""

from roof_api.segmentation.mask import segment_roof_mask

__all__ = ["segment_roof_mask"]
