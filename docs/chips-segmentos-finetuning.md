# Fine-tuning com chips_segmentos (3 classes: fundo, linha, água)

Os ficheiros **NPZ** em `roof/chips_segmentos/gt/` contêm segmentos de linha (linhas divisorias entre telhados e entre águas). A partir deles é possível gerar **máscaras de 3 classes** para fine-tuning de um modelo (ex.: DeepLabV3+) com as classes:

- **0 = fundo (nada)** — borda da imagem
- **1 = linha divisória** — linhas do NPZ (entre telhados / entre águas)
- **2 = água** — cada plano do telhado (cada “quadradinho” branco); o **telhado** é o conjunto das águas dentro das bordas

O modelo atual multiclasse (águas, claraboia, divisória, laje) foi treinado em `chips_multiclass`. Este fluxo usa **chips_segmentos** (imagens + NPZ + building_masks) para treinar com foco em **linha divisória vs água vs fundo**.

## 1. Gerar as máscaras 3-class

Na raiz do projeto:

```bash
python -m scripts.generate_finetuning_masks_from_segmentos --segmentos_dir roof/chips_segmentos
```

Por defeito as máscaras são gravadas em `roof/chips_segmentos/masks_3class/`. Cada pixel tem valor 0, 1 ou 2 (fundo, linha, água). Opções úteis:

- `--out_masks NOME` — gravar noutra subpasta (ex.: `masks_3class`)
- `--line_thickness 2` — espessura das linhas em px
- `--border 5` — largura da faixa de borda (classe fundo) em px

## 2. building_masks e padronização de nomes

A pasta **building_masks** contém desenhos dos telhados (binário: telhado branco, fundo preto), com nomes como `0100.png`, `0101.png`, … Para alinhar às imagens `segmentos_000000.png`, …:

```bash
python -m scripts.standardize_building_masks_names
```

Isso copia para **building_masks_renamed/** com nomes `segmentos_000000.png`, etc. Para gerar **masks_3class** usando esses telhados (em vez do preenchimento por contornos) e sobrepor as linhas do NPZ:

```bash
python -m scripts.generate_finetuning_masks_from_segmentos --segmentos_dir roof/chips_segmentos --out_masks masks_3class --border 0 --use_building_masks building_masks_renamed
```

## 3. Estrutura resultante

```
roof/chips_segmentos/
├── images/               # imagens RGB
├── gt/                   # NPZ com chave 'lines'
├── building_masks/       # telhados desenhados (nomes 0100.png, …)
├── building_masks_renamed/  # mesmos, com nomes segmentos_000000.png, …
├── masks/                # máscaras binárias de linhas
└── masks_3class/         # máscaras 0/1/2 para fine-tuning
```

Para treino: **images** = `images/`, **masks** = `masks_3class/`, **num_classes** = 3.

## 4. Usar no treino (notebook Kaggle ou local)

O notebook **kaggle_train_roof_deeplabv3.ipynb** implementa o pipeline em **3 etapas**:

1. **Pré-treino binário** (archive + chips) → `deeplabv3_roof_pretrain.pt`
2. **Fine-tuning segmentos** (chips_segmentos: images + masks_3class) → `deeplabv3_roof_segmentos.pt` (carrega o pré-treino)
3. **Fine-tuning multiclasse** (chips_multiclass) → `deeplabv3_roof_multiclass.pt` (carrega segmentos ou pré-treino)

Para a etapa 2, usa **RoofDataset** com `num_classes=3` e **CrossEntropyLoss**. O notebook procura `masks_3class/` em chips_segmentos; se não existir, usa `masks/`.

Mapeamento de classes no treino: 0 = fundo, 1 = linha divisória, 2 = água (cada plano; telhado = conjunto das águas).

## 5. Relação com o modelo multiclasse atual

| Dataset | Classes | Uso |
|--------|---------|-----|
| chips_multiclass | 0=fundo, 1=águas, 2=claraboia, 3=divisória, 4=laje | Modelo em produção (`deeplabv3_roof_multiclass.pt`) |
| chips_segmentos (masks) | binário (linha vs resto) | Legado / análise |
| chips_segmentos (masks_3class) | 0=fundo, 1=linha, 2=água (plano) | Etapa 2 do pipeline → `deeplabv3_roof_segmentos.pt` |

Os NPZ não têm polígonos de água nem fundo; o script (ou building_masks) define cada região fechada como **água** (plano do telhado) e fundo = borda da imagem. O telhado é o conjunto das águas dentro das bordas.
