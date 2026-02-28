# Treinar um modelo para prever linhas (wireframes) em imagens novas

Os **.npz** do RoofSat têm segmentos de linha (contornos e águas dos telhados). Para treinar um modelo que **veja essas linhas em imagens novas**, a abordagem mais simples é:

1. **Converter os .npz em máscaras binárias** (“mapa de linhas”): desenhar cada segmento num imagem preta; pixels das linhas = 1, resto = 0.
2. **Treinar uma U-Net (binária)** para prever esse mapa a partir da imagem: entrada = imagem RGB, saída = probabilidade de “pixel em cima de uma linha”.
3. **Em imagens novas:** correr o modelo → obter o mapa de linhas → opcionalmente extrair segmentos (ex.: Hough ou esqueletização) se precisares de `[[x1,y1],[x2,y2]]`.

Assim reutilizas o mesmo pipeline de treino (U-Net) que já tens; só mudas o “alvo” de máscara de telhado para mapa de linhas.

---

## Passo 1: Criar o dataset (imagens + mapa de linhas)

O script **`scripts/prepare_line_dataset_from_npz.py`** (ver abaixo) faz o seguinte:

- Para cada imagem em `Roofsat/img_color/` (ou `img/`) que tenha um .npz correspondente em `gt/`:
  - Carrega o .npz e desenha os segmentos numa imagem preta (mesmo tamanho da imagem).
  - Grava em `line_dataset/images/` e `line_dataset/masks/` (máscara = mapa de linhas binário).

Fica um dataset no formato **images/ + masks/** que o `train_unet` já aceita.

---

## Passo 2: Treinar o modelo

Treino **binário** (um canal de saída: “linha” vs “não linha”):

```bash
python -m scripts.train_unet --data_dir line_dataset --output ./models/unet_lines.pt --num_classes 1 --epochs 40 --size 512 512
```

(Se as imagens forem 550×550, podes usar `--size 550 550` ou deixar o redimensionamento para 512.)

---

## Passo 3: Usar em imagens novas

1. Carregar o modelo e a imagem nova.
2. Prever o mapa de linhas (probabilidade por pixel).
3. (Opcional) Binarizar (threshold) e extrair segmentos com **Hough** ou outro método:

```python
import cv2
import numpy as np

# Exemplo: após obter pred (H, W) em [0,1]
pred_bin = (pred > 0.5).astype(np.uint8) * 255
segments = cv2.HoughLinesP(pred_bin, 1, np.pi/180, threshold=50, minLineLength=20, maxLineGap=5)
# segments: (N, 1, 4) -> x1, y1, x2, y2
```

Assim passas de “mapa de linhas” a “lista de segmentos” em imagens novas.

---

## Resumo

| Etapa | O que fazer |
|-------|-------------|
| Dados | `prepare_line_dataset_from_npz.py` → pasta com `images/` e `masks/` (mapa de linhas) |
| Treino | `train_unet --data_dir line_dataset --num_classes 1 --output unet_lines.pt` |
| Inferência | Modelo → mapa de linhas → (opcional) Hough/skeleton → segmentos `[[x1,y1],[x2,y2]]` |

Os .npz só entram na **preparação do dataset** (para gerar as máscaras de treino). O modelo aprende a prever o **mapa de linhas**; em imagens novas esse mapa pode depois ser convertido em linhas explícitas com métodos clássicos (Hough, etc.).
