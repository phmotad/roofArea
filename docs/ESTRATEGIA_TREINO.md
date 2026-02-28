# Estratégia de treino — segmentação de telhados

## O que cada dataset tem

| Dataset | Imagens | Máscaras | Uso |
|--------|---------|----------|-----|
| **chips_multiclass** | Satélite (`images/`) | **Multiclasse** (`masks/`): fundo, águas do telhado, claraboias, divisórias, laje | Fine-tuning: aprender as classes finais do teu domínio |
| **dados_inria** | Satélite (`images/`) | **Binário** (`masks/`): telhado vs não-telhado | Pré-treino: aprender “o que é telhado” com muito mais exemplos |
| **RoofSat** | Satélite (`img_color/`) | **Binário** (`building_masks/`): edifício/telhado vs fundo | Pré-treino: mais dados binários, outro tipo de cena (Pleiades) |
| **RoofSat** | — | **gt/*.npz** | Segmentos de linha (chave `lines`): cada segmento é `[[x1,y1],[x2,y2]]` (contornos e divisões das águas). Não é máscara; não entra no treino da U-Net. Uso: visualização ou modelos de linhas (ex.: LineFit). Ver `dados_inria/Roofsat/COMO_USAR_ROOFSAT.md` e `load_roofsat_wireframe()` em `dataset.py`. |

Resumo:
- **Inria** e **RoofSat (building_masks)** = só “telhado sim/não” (binário).
- **chips_multiclass** = “telhado + onde estão águas, claraboias, divisórias, laje” (multiclasse).

Os **.npz** do RoofSat descrevem as divisões das águas em segmentos de linha; não são usados no treino atual da U-Net (que usa máscaras pixel a pixel).

---

## Estratégia que estamos a usar

1. **Pré-treino binário** (opcional mas recomendado)  
   Treinar a U-Net com **num_classes=1** em dados onde a máscara é só “telhado vs fundo”:
   - **Inria** (muitos patches)
   - e/ou **RoofSat** (building_masks + img_color)

   Objetivo: o modelo aprender a localizar telhado/edifício antes de distinguir águas, claraboias, etc.

2. **Fine-tuning multiclasse**  
   Treinar com **num_classes=5** (ou o teu número de classes) em **chips_multiclass**, carregando o checkpoint do pré-treino (`--pretrain ...`).

   Objetivo: reutilizar o encoder (e parte do decoder) já sensível a “telhado” e afinar + aprender as classes finais (águas, claraboia, divisória, laje) nos teus chips.

Fluxo no Kaggle: pré-treino Inria → (opcional) pré-treino RoofSat → fine-tuning chips_multiclass com o melhor checkpoint.

---

## Juntar Inria + RoofSat para pré-treino binário

Sim, podes **juntar as imagens e máscaras** de Inria e RoofSat num único dataset binário para um único pré-treino com mais dados.

- **Inria:** `dados_inria/images/` + `dados_inria/masks/` (patches 512×512, nomes tipo `inria_000001.png`).
- **RoofSat:** `dados_inria/Roofsat/img_color/` + `building_masks/` (550×550, IDs em `train.txt`/`val.txt`).

Ambos são “telhado vs fundo”; a resolução e o tamanho são diferentes, mas o `train_unet` redimensiona para o `--size` (ex.: 512×512), por isso podem ser misturados.

**Formas de “juntar”:**

1. **Script que copia para uma pasta única**  
   Cria uma pasta (ex.: `dados_binario_inria_roofsat/`) com:
   - `images/`: cópias de todos os ficheiros de `dados_inria/images/` e de `Roofsat/img_color/` (com nomes únicos, ex. `inria_000001.png`, `roofsat_0100.png`).
   - `masks/`: o mesmo para as máscaras (mesmos nomes que em `images/`).

   Depois:  
   `python -m scripts.train_unet --data_dir dados_binario_inria_roofsat --output ./models/unet_binario.pt --num_classes 1 --epochs 30`

2. **No Kaggle**  
   O notebook hoje faz pré-treino Inria e depois (opcional) RoofSat em sequência. Juntar os dois num único dataset (como em 1) daria um único pré-treino binário com Inria + RoofSat em vez de dois passos.

**Script para juntar:** `scripts/merge_inria_roofsat_binary.py`

```bash
python -m scripts.merge_inria_roofsat_binary --output dados_binario_inria_roofsat
python -m scripts.train_unet --data_dir dados_binario_inria_roofsat --output ./models/unet_binario.pt --num_classes 1 --epochs 30
```

A pasta `dados_binario_inria_roofsat` fica com `images/` e `masks/` (nomes únicos: `inria_*.png` e `roofsat_*.png`). Depois podes usar esse checkpoint como `--pretrain` no fine-tuning com chips_multiclass.
