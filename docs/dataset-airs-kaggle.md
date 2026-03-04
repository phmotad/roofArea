# Dataset AIRS (Kaggle) — Aerial Imagery for Roof Segmentation

O dataset **[Aerial Imagery for Roof Segmentation](https://www.kaggle.com/datasets/atilol/aerialimageryforroofsegmentation)** (atilol no Kaggle) é o **AIRS** — benchmark de segmentação de **telhados** a partir de imagens aéreas. Muito alinhado com o nosso objetivo (telhado vs fundo).

---

## Características

| Aspecto | Valor |
|--------|--------|
| **Cobertura** | ~457 km² de ortofoto |
| **Edifícios** | >220 000 |
| **Resolução** | 7,5 cm (0,075 m) |
| **Ground truth** | Máscaras de **contorno de telhado** (não footprint de edifício), alinhadas à imagem |
| **Tarefa** | Segmentação semântica: pixel = telhado ou não |
| **Referência** | Chen et al., 2019; [airs-dataset.com](https://www.airs-dataset.com/); [Papers with Code](https://paperswithcode.com/dataset/airs) |

É **binário** (telhado vs fundo), ideal para **pré-treino** do nosso DeepLabV3+ ou para aumentar os dados de `roof/chips`.

---

## Como usar no nosso projeto

### 1. No Kaggle (notebook de treino)

1. No [Kaggle](https://www.kaggle.com/datasets/atilol/aerialimageryforroofsegmentation), clica em **Add to notebook** / anexa o dataset ao teu notebook (ex.: `kaggle_train_roof_deeplabv3`).
2. O dataset fica em `/kaggle/input/aerialimageryforroofsegmentation/` (o nome exacto pode variar — verifica em **Data** no notebook).
3. A estrutura típica do AIRS é **train** / **val** / **test**, cada um com subpastas de imagens e máscaras (ex.: `train/image`, `train/label` ou `train/images`, `train/masks`). Os nomes podem ser `image`/`label` ou `images`/`masks`.
4. No notebook, usa este dataset como **CHIPS_BIN_PATH** para o pré-treino binário: aponta `images_dir` e `masks_dir` para as pastas corretas dentro do dataset (ex.: `train/image` e `train/label`). Se a estrutura usar outros nomes, ajusta no código que descobre os pares ou passa caminhos explícitos.

Assim **conseguimos usar o dataset AIRS para treinar o nosso modelo**: como fonte de pré-treino (telhado vs fundo) no mesmo notebook onde já tens roof/chips e chips_multiclass.

### 2. Estrutura esperada pelo nosso pipeline

O `RoofDataset` e o notebook esperam:

- **images/** (ou pasta equivalente): imagens RGB (PNG/JPG).
- **masks/** (ou equivalente): máscaras com **telhado = valor > 0**, fundo = 0 (PNG em tons de cinza ou binário).

Se o AIRS tiver, por exemplo, `train/image` e `train/label`, no notebook podes definir:

- `AIRS_TRAIN_IMAGES = "/kaggle/input/aerialimageryforroofsegmentation/train/image"`
- `AIRS_TRAIN_MASKS = "/kaggle/input/aerialimageryforroofsegmentation/train/label"`

e usar esses caminhos para o pré-treino binário (ou concatenar com roof/chips se o dataset suportar múltiplas pastas). Se as máscaras forem 0/255, já estão no formato certo; se forem 0/1, o nosso loader trata (threshold em 127 ou > 0).

### 3. Estrutura local (roof/archive)

No repositório, **roof/archive** segue a mesma estrutura do AIRS no Kaggle:

- `roof/archive/train/image/*.tif` e `roof/archive/train/label/*.tif`
- `roof/archive/val/image/*.tif` e `roof/archive/val/label/*.tif`
- `roof/archive/test/image/*.tif` e `roof/archive/test/label/*.tif`

Ao descarregar o dataset do Kaggle para uso local, extrair (ou copiar) os conteúdos para estas pastas. Ver `roof/archive/README.md`.

### 4. Citação

Se usares o AIRS nos teus resultados:

```text
Chen, K. et al. (2019). Aerial imagery for roof segmentation: A large-scale dataset towards 
automatic mapping of buildings. (Referência completa no paper ou em airs-dataset.com.)
```

---

## Resumo

- **Dataset:** [Kaggle – Aerial Imagery for Roof Segmentation](https://www.kaggle.com/datasets/atilol/aerialimageryforroofsegmentation).
- **Estrutura:** `train/image/*.tif`, `train/label/*.tif` (e idem para `val`, `test`). No repositório, **roof/archive** segue esta estrutura (ver `roof/archive/README.md`).
- **Uso:** Pré-treino binário (telhado vs fundo); formato compatível com o pipeline (RGB + máscara binária).
- **Conseguir para treinar:** No Kaggle — anexar o dataset ao notebook; localmente — descarregar e extrair em `roof/archive` com as pastas acima.
