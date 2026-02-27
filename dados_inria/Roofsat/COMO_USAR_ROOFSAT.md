# Como usar o RoofSat no projeto roofApi

O RoofSat traz **imagens de telhado**, **máscaras de edifício** e **ground-truth em NPZ** (wireframes). No roofApi usamos assim:

---

## 1. Segmentação binária (U-Net) — imagens + máscaras

Para treinar ou avaliar a U-Net de segmentação de telhados/edifícios:

- **Imagens:** `img_color/` (RGB, 550×550) ou `img/` (grayscale).
- **Máscaras:** `building_masks/` (binário: edifício vs fundo).

Os ficheiros `train.txt`, `val.txt` e `test.txt` listam os IDs (um por linha, sem extensão) para cada split. O código usa estes splits através do dataset `RoofSatDataset` (ver `src/roof_api/segmentation/dataset.py`).

**Exemplo:** treino só com RoofSat (binário):

```bash
python -m scripts.train_unet --data_dir dados_inria/Roofsat --dataset_type roofsat --output ./models/unet_roofsat.pt --num_classes 1 --epochs 30
```

Ou em Python:

```python
from roof_api.segmentation.dataset import RoofSatDataset
ds = RoofSatDataset("dados_inria/Roofsat", split="train", size=(256, 256), augment=True)
x, y = ds[0]  # x: (3,H,W), y: (1,H,W) binário
```

---

## 2. Wireframes (segmentos de linha) — ficheiros .npz

A pasta **`gt/`** contém (na versão completa do dataset) ficheiros **.npz** com o ground-truth de wireframes:

- Chave: **`lines`**
- Formato: segmentos de linha `[[x1, y1], [x2, y2]]` (contornos e esqueletos de telhados).

Isto **não** é máscara pixel a pixel; é uma representação em linhas (grafos planares), útil para:

- Visualização de contornos de telhado.
- Modelos de detecção de linhas / ajuste geométrico (ex. LineFit, ECCV 2024).

**Carregar wireframes em Python:**

```python
import numpy as np

data = np.load("dados_inria/Roofsat/gt/0100.npz", allow_pickle=True)
lines = data["lines"]  # array de segmentos [[[x1,y1],[x2,y2]], ...]
```

Se na tua cópia do RoofSat a pasta `gt/` tiver apenas `.svg`, o formato NPZ pode estar noutra distribuição do dataset; o código acima aplica-se quando existirem `.npz`.

---

## Resumo

| Dados              | Uso no projeto                          |
|--------------------|-----------------------------------------|
| `img_color/` + `building_masks/` | U-Net: segmentação binária (edifício) |
| `train/val/test.txt`             | Splits para treino/validação/teste     |
| `gt/*.npz` (`lines`)             | Wireframes: visualização ou pipelines de linhas |

Os zips para o Kaggle (script `scripts/prepare_kaggle_zips.py`) incluem a pasta **Roofsat** opcional; no notebook atual o treino usa Inria + chips. Para usar RoofSat no Kaggle, basta apontar o dataset para a pasta Roofsat e usar `RoofSatDataset` ou converter RoofSat para `images/`+`masks/` com o mesmo formato que o Inria.
