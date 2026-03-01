# Estrutura roof/ e os dois modelos

## Estrutura de pastas **roof/**

Criada por **`scripts/prepare_roof_structure.py`** (ou manualmente):

```
roof/
├── chips/              # Pré-treino binário (telhado vs fundo)
│   ├── images/         # chip_000001.png, chip_000002.png, ... (Inria + RoofSat)
│   └── masks/
├── chips_multiclass/   # Fine-tuning multiclasse
│   ├── images/         # multiclass_000001.png, ...
│   └── masks/
└── chips_segmentos/    # Modelo de linhas (águas do telhado)
    ├── images/         # segmentos_000001.png, ...
    ├── gt/             # segmentos_000001.npz, ... (ground truth em segmentos)
    └── masks/          # (gerado por rasterize_chips_segmentos_masks.py)
```

- **chips:** junta Inria + RoofSat com nomes padronizados (`chip_*.png`).
- **chips_multiclass:** cópia do teu dataset multiclasse com nomes `multiclass_*.png`.
- **chips_segmentos:** imagens + .npz do RoofSat (só onde existe .npz); **masks/** é preenchido ao rasterizar os .npz (mapa de linhas).

---

## Classes em chips_multiclass (5 classes)

Para o modelo identificar **telhado**, **divisorias entre casas**, **águas**, **claraboias** e **lajes**, as máscaras devem usar estes valores de pixel:

| Classe | Valor | Descrição |
|--------|-------|-----------|
| Fundo | 0 | Tudo o que não é telhado (solo, ruas, vegetação). |
| Águas | 1 | Planos inclinados do telhado (cada “água” é um plano). |
| Claraboia | 2 | Claraboias / janelas de telhado. |
| **Divisória** | 3 | **Fronteira entre telhados de casas diferentes** (quando dois telhados estão “grudados”). Marcar bem esta classe permite à API separar casa a casa. |
| Laje | 4 | Lajes / coberturas planas. |

**Anotação:** Nas imagens onde dois ou mais telhados de casas diferentes se tocam, desenhar a **divisória** (classe 3) na linha de fronteira entre edifícios. O modelo usa esta classe para não misturar águas de casas diferentes.

---

## Como fica o treino (notebook Kaggle)

1. **Construir roof/** — Se não existir uma pasta `roof/` em input, o notebook descarrega Inria (se necessário), corre `prepare_roof_structure` e gera `/kaggle/working/roof`.
2. **Pré-treino binário** — Treina em `roof/chips` → guarda `unet_roof_pretrain.pt`.
3. **Fine-tuning multiclasse** — Treina em `roof/chips_multiclass` com `--pretrain unet_roof_pretrain.pt` → guarda **`unet_roof_multiclass.pt`**.
4. **Modelo de linhas** — Gera `roof/chips_segmentos/masks/` a partir dos .npz; treina em `roof/chips_segmentos` → guarda **`unet_lines.pt`**.

---

## Os dois modelos no final

| Modelo | Ficheiro | Entrada | Saída | Uso |
|--------|----------|---------|--------|-----|
| **U-Net multiclasse** | `unet_roof_multiclass.pt` | Imagem RGB | Máscara com classes (0=fundo, 1=águas, 2=claraboia, 3=divisória, 4=laje) | Segmentação semântica do telhado |
| **U-Net linhas** | `unet_lines.pt` | Imagem RGB | Mapa de probabilidade “pixel em cima de linha” (binário) | Ver linhas das águas; em inferência podes usar Hough (ou outro) para obter segmentos `[[x1,y1],[x2,y2]]` |

- O **multiclasse** diz *que* tipo de superfície cada pixel é (incluindo águas).
- O **linhas** diz *onde* estão as arestas/linhas (contornos e divisões das águas). Os dois podem ser usados em conjunto: multiclasse para máscaras por classe, linhas para refinamento ou extração de segmentos.

---

## Criar roof/ no teu PC

Na raiz do projeto (com `dados_inria`, `chips_multiclass`, `dados_inria/Roofsat`):

```bash
python -m scripts.prepare_roof_structure --output roof
python -m scripts.rasterize_chips_segmentos_masks --segmentos_dir roof/chips_segmentos
```

Depois podes comprimir a pasta **roof/** e subir como um único dataset no Kaggle; o notebook usa essa pasta diretamente (sem ter de construir a partir de vários datasets).
