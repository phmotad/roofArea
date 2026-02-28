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

### O que contêm

A pasta **`gt/`** contém (na versão completa do dataset) ficheiros **.npz** com ground-truth em **linhas**, não em pixels:

- **Chave:** `lines`
- **Formato:** lista de segmentos; cada segmento é `[[x1, y1], [x2, y2]]` (dois pontos que definem uma aresta).
- **Significado:** contornos dos telhados e divisões das águas (arestas do “grafo” do telhado).

Isto **não** é máscara pixel a pixel. A U-Net de segmentação que treinamos usa só **imagens + máscaras** (`img_color` + `building_masks`); os **.npz não entram no treino** da U-Net.

### Para que servem os .npz

- **Visualização:** desenhar as linhas por cima da imagem para ver contornos e águas.
- **Modelos de linhas:** treinar ou avaliar métodos que preveem segmentos de linha (ex.: LineFit, ECCV 2024), ou usar como ground-truth para extrair divisões de águas.

### Como usar no código

**Carregar os segmentos** (função do projeto):

```python
from pathlib import Path
from roof_api.segmentation.dataset import load_roofsat_wireframe

# lines tem forma (N, 2, 2): N segmentos, cada um com dois pontos (x,y)
lines = load_roofsat_wireframe(Path("dados_inria/Roofsat/gt/0100.npz"))
```

**Desenhar as linhas em cima da imagem** (exemplo com OpenCV):

```python
import cv2
import numpy as np
from pathlib import Path
from roof_api.segmentation.dataset import load_roofsat_wireframe

img = cv2.imread("dados_inria/Roofsat/img_color/0100.png")
lines = load_roofsat_wireframe(Path("dados_inria/Roofsat/gt/0100.npz"))
for seg in lines:
    pt1 = (int(seg[0, 0]), int(seg[0, 1]))
    pt2 = (int(seg[1, 0]), int(seg[1, 1]))
    cv2.line(img, pt1, pt2, (0, 255, 0), 1)
# Guardar ou mostrar img
```

Se na tua cópia do RoofSat a pasta `gt/` tiver apenas `.svg`, o formato NPZ pode vir noutra distribuição do dataset; o código aplica-se quando existirem `.npz`.

**Treinar um modelo para prever linhas em imagens novas:** os .npz servem como ground truth para criar um dataset “imagem → mapa de linhas” e treinar uma U-Net binária. Ver **`docs/TREINO_LINHAS_NPZ.md`** e o script **`scripts/prepare_line_dataset_from_npz.py`**.

---

## Resumo

| Dados              | Uso no projeto                          |
|--------------------|-----------------------------------------|
| `img_color/` + `building_masks/` | U-Net: segmentação binária (edifício) |
| `train/val/test.txt`             | Splits para treino/validação/teste     |
| `gt/*.npz` (`lines`)             | Wireframes: visualização ou pipelines de linhas |

Os zips para o Kaggle (script `scripts/prepare_kaggle_zips.py`) incluem a pasta **Roofsat** opcional; no notebook atual o treino usa Inria + chips. Para usar RoofSat no Kaggle, basta apontar o dataset para a pasta Roofsat e usar `RoofSatDataset` ou converter RoofSat para `images/`+`masks/` com o mesmo formato que o Inria.
