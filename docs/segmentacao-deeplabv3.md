# Segmentação principal: DeepLabV3+

A API usa **DeepLabV3+** (torchvision) como **único** modelo de segmentação principal para telhados e águas. O modelo de linhas (opcional) continua a ser U-Net.

## Configuração (.env)

| Variável | Valor | Descrição |
|----------|--------|-----------|
| `SEGMENTATION_MODEL_PATH` | `./models/deeplabv3_roof_multiclass.pt` | Caminho do checkpoint DeepLabV3+ (state_dict ou dict com chave `model`). |
| `SEGMENTATION_NUM_CLASSES` | `5` | Número de classes: 0=fundo, 1=águas, 2=claraboia, 3=divisória, 4=laje. |
| `SEGMENTATION_DEEPLAB_BACKBONE` | `resnet50` | Backbone: `resnet50`, `resnet101` ou `mobilenet_v3_large`. |
| `SEGMENTATION_LINES_MODEL_PATH` | (opcional) | U-Net de linhas; se vazio, não desenha linhas. |

Exemplo:

```env
SEGMENTATION_MODEL_PATH=./models/deeplabv3_roof_multiclass.pt
SEGMENTATION_NUM_CLASSES=5
SEGMENTATION_DEEPLAB_BACKBONE=resnet50
```

## Checkpoint

O ficheiro em `SEGMENTATION_MODEL_PATH` deve ser um checkpoint **DeepLabV3+** treinado (ex.: com o notebook Kaggle). Formato esperado:

- `torch.save({"model": model.state_dict(), "num_classes": 5}, path)` ou
- `torch.save(model.state_dict(), path)`

O modelo deve ser DeepLabV3 da torchvision com o mesmo `num_classes` e backbone configurados.

## Treino

Usa o notebook **`notebooks/kaggle_train_roof_deeplabv3.ipynb`** no Kaggle (GPU) para treinar com o dataset **roof/chips_multiclass** (5 classes). O checkpoint gerado é compatível com `load_deeplabv3` na API.

## Comportamento

- **Máscara de telhados:** `segment_roof_mask()` usa DeepLabV3+ e devolve máscara binária (telhado = 1 - prob(fundo)).
- **Máscara de águas:** `segment_waters_mask()` usa a classe 1 (águas) do modelo multiclasse.
- **Modelo de linhas:** U-Net em `SEGMENTATION_LINES_MODEL_PATH` (opcional).

## Dependência

`torchvision>=0.15.0` no `pyproject.toml`. Instala com `pip install -e .`.
