"""Testar carregamento e inferência do modelo DeepLabV3+. Correr na raiz: python -m scripts.test_models"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    try:
        import torch
        from roof_api.segmentation.deeplabv3_model import load_deeplabv3, predict_roof_prob, predict_multiclass_probs
    except ImportError as e:
        print("Erro ao importar (instala: pip install -e . torch torchvision):", e)
        return 1

    models_dir = ROOT / "models"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)

    import numpy as np
    rng = np.random.default_rng(42)
    rgb = rng.integers(0, 256, (128, 128, 3), dtype=np.uint8)

    path = models_dir / "deeplabv3_roof_multiclass.pt"
    if not path.exists():
        print("[SKIP] deeplabv3_roof_multiclass.pt — ficheiro não encontrado:", path)
        return 0

    try:
        model = load_deeplabv3(str(path), device, num_classes=5, backbone="resnet50")
        prob = predict_roof_prob(model, rgb, device)
        assert prob.shape == rgb.shape[:2], f"forma esperada {rgb.shape[:2]}, obtida {prob.shape}"
        assert prob.dtype == np.float32
        print("[OK] deeplabv3_roof_multiclass.pt — predict_roof_prob forma", prob.shape, "min/max", round(float(prob.min()), 4), round(float(prob.max()), 4))
        probs = predict_multiclass_probs(model, rgb, device)
        assert probs.shape[:2] == rgb.shape[:2] and probs.shape[2] == 5
        print("[OK] deeplabv3_roof_multiclass.pt — predict_multiclass_probs forma", probs.shape)
    except Exception as e:
        print("[FAIL] deeplabv3_roof_multiclass.pt —", e)
        return 1

    print("\nResultado: modelo DeepLabV3+ testado com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
