"""Script para testar carregamento e inferência dos modelos U-Net. Correr na raiz: python -m scripts.test_models"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def main():
    try:
        import torch
        from roof_api.segmentation.unet_model import load_unet, predict
    except ImportError as e:
        print("Erro ao importar (instala: pip install -e . torch):", e)
        return 1

    models_dir = ROOT / "models"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)

    # Imagem sintética 128x128
    rng = __import__("numpy").random.default_rng(42)
    rgb = rng.integers(0, 256, (128, 128, 3), dtype=__import__("numpy").uint8)

    results = []
    for name, path, num_classes in [
        ("unet_roof_pretrain", models_dir / "unet_roof_pretrain.pt", 1),
        ("unet_roof_multiclass", models_dir / "unet_roof_multiclass.pt", 5),
        ("unet_lines", models_dir / "unet_lines.pt", 1),
    ]:
        if not path.exists():
            print("[SKIP]", name, "— ficheiro não encontrado:", path)
            results.append((name, False, "ficheiro não encontrado"))
            continue
        try:
            model = load_unet(str(path), device, num_classes=num_classes)
            out = predict(model, rgb, device)
            assert out.shape == rgb.shape[:2], f"forma esperada {rgb.shape[:2]}, obtida {out.shape}"
            assert out.dtype == __import__("numpy").float32
            print("[OK]", name, "— forma", out.shape, "dtype", out.dtype, "min/max", round(float(out.min()), 4), round(float(out.max()), 4))
            results.append((name, True, None))
        except Exception as e:
            print("[FAIL]", name, "—", e)
            results.append((name, False, str(e)))

    ok = sum(1 for _, success, _ in results if success)
    total = len(results)
    print()
    print(f"Resultado: {ok}/{total} modelos testados com sucesso.")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
