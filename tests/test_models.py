"""Testes de carregamento e inferência do modelo DeepLabV3+."""

from pathlib import Path

import numpy as np
import pytest

try:
    import torch
    import torchvision  # noqa: F401
    from roof_api.segmentation.deeplabv3_model import (
        load_deeplabv3,
        predict_roof_prob,
        predict_multiclass_probs,
    )
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"


def _sample_rgb(h: int = 128, w: int = 128) -> np.ndarray:
    """Imagem RGB sintética para teste (HxWx3 uint8)."""
    rng = np.random.default_rng(42)
    return rng.integers(0, 256, (h, w, 3), dtype=np.uint8)


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch/roof_api não disponível (pip install -e . torch torchvision)")
def test_load_deeplabv3_multiclass():
    """Carrega deeplabv3_roof_multiclass.pt e corre inferência (roof prob e multiclass)."""
    path = MODELS_DIR / "deeplabv3_roof_multiclass.pt"
    if not path.exists():
        pytest.skip("models/deeplabv3_roof_multiclass.pt não encontrado")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_deeplabv3(str(path), device, num_classes=5, backbone="resnet50")
    rgb = _sample_rgb()
    prob = predict_roof_prob(model, rgb, device)
    assert prob.shape == rgb.shape[:2], "saída roof prob deve ser HxW"
    assert prob.dtype == np.float32
    assert prob.size > 0
    probs = predict_multiclass_probs(model, rgb, device)
    assert probs.shape[:2] == rgb.shape[:2] and probs.shape[2] == 5


@pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch/roof_api não disponível (pip install -e . torch torchvision)")
def test_at_least_one_model_present():
    """Garante que pelo menos um modelo existe para os testes não serem todos skipped."""
    path = MODELS_DIR / "deeplabv3_roof_multiclass.pt"
    assert path.exists(), (
        "Coloca o modelo em models/deeplabv3_roof_multiclass.pt para testar."
    )
