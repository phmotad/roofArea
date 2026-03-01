"""Testes de carregamento e inferência dos modelos U-Net (unet_roof_pretrain, unet_roof_multiclass, unet_lines)."""

import os
from pathlib import Path

import numpy as np
import pytest

try:
    import torch
    from roof_api.segmentation.unet_model import load_unet, predict
    TORCH_AVAILABLE = True
except ImportError as e:
    TORCH_AVAILABLE = False
    _import_error = e

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"


def _sample_rgb(h: int = 128, w: int = 128) -> np.ndarray:
    """Imagem RGB sintética para teste (HxWx3 uint8)."""
    rng = np.random.default_rng(42)
    return (rng.integers(0, 256, (h, w, 3), dtype=np.uint8))


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch/roof_api não disponível (pip install -e . torch)")
def test_load_unet_pretrain():
    """Carrega unet_roof_pretrain.pt e corre uma inferência."""
    path = MODELS_DIR / "unet_roof_pretrain.pt"
    if not path.exists():
        pytest.skip("models/unet_roof_pretrain.pt não encontrado")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_unet(str(path), device, num_classes=1)
    rgb = _sample_rgb()
    out = predict(model, rgb, device)
    assert out.shape == rgb.shape[:2], "saída deve ser HxW"
    assert out.dtype == np.float32
    assert out.size > 0


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch/roof_api não disponível (pip install -e . torch)")
def test_load_unet_multiclass():
    """Carrega unet_roof_multiclass.pt e corre uma inferência (prob. classe água)."""
    path = MODELS_DIR / "unet_roof_multiclass.pt"
    if not path.exists():
        pytest.skip("models/unet_roof_multiclass.pt não encontrado")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_unet(str(path), device, num_classes=5)
    rgb = _sample_rgb()
    out = predict(model, rgb, device)
    assert out.shape == rgb.shape[:2]
    assert out.dtype == np.float32
    assert 0 <= out.min() <= out.max() <= 1.0 + 1e-5, "saída deve ser probabilidades"


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch/roof_api não disponível (pip install -e . torch)")
def test_load_unet_lines():
    """Carrega unet_lines.pt e corre uma inferência (mapa de linhas)."""
    path = MODELS_DIR / "unet_lines.pt"
    if not path.exists():
        pytest.skip("models/unet_lines.pt não encontrado")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_unet(str(path), device, num_classes=1)
    rgb = _sample_rgb()
    out = predict(model, rgb, device)
    assert out.shape == rgb.shape[:2]
    assert out.dtype == np.float32


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch/roof_api não disponível (pip install -e . torch)")
def test_at_least_one_model_present():
    """Garante que pelo menos um modelo existe para os testes não serem todos skipped."""
    candidates = [
        MODELS_DIR / "unet_roof_pretrain.pt",
        MODELS_DIR / "unet_roof_multiclass.pt",
        MODELS_DIR / "unet_lines.pt",
    ]
    assert any(p.exists() for p in candidates), (
        "Coloca pelo menos um modelo em models/ (ex.: unet_roof_multiclass.pt) para testar."
    )
