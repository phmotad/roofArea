# Treino do modelo U-Net para segmentação de telhados

O modelo U-Net usado em produção é treinado com pares **imagem RGB (ortofoto)** e **máscara binária (telhado = 1, resto = 0)**. O checkpoint gerado é o mesmo carregado pela API (`SEGMENTATION_MODEL_PATH`).

## O que precisas (checklist)

| Item | Descrição |
|------|-----------|
| **1. Imagens RGB** | Ortofoto ou satélite onde se vejam telhados (Mapbox, DGT, Sentinel, etc.). Cortes/tiles em PNG ou JPG. |
| **2. Máscaras binárias** | Uma máscara por imagem: **telhado = branco (255)**, resto = preto (0). Mesmo nome de ficheiro que a imagem (ex.: `tile_001.png` → `tile_001.png` em `masks/`). |
| **3. Estrutura de pastas** | Uma pasta com duas subpastas: `images/` e `masks/`, com os pares com o mesmo nome base. |
| **4. Ambiente** | Python 3.10+, dependências do projeto (`pip install -e .`). Opcional: GPU com CUDA para treino mais rápido. |
| **5. Quantidade** | Mínimo ~100–200 pares; 300–1000+ costumam dar resultados estáveis. |

**Como obter as máscaras:** desenhar à mão em QGIS/ArcGIS sobre a ortofoto e exportar como imagem binária; ou usar dados LIDAR/DSM para extrair telhados e depois limpar; ou converter um dataset público de segmentação de telhados para este formato.

## Formato dos dados

Estrutura de pastas:

```
data/roof/          (ou qualquer --data_dir)
├── images/         (nome configurável com --images)
│   ├── tile_001.png
│   ├── tile_002.jpg
│   └── ...
└── masks/          (nome configurável com --masks)
    ├── tile_001.png   (mesmo nome base que em images/)
    ├── tile_002.png
    └── ...
```

- **images:** Ortofoto ou imagem de satélite em RGB (PNG, JPG, TIF ou **.npy**). Qualquer resolução; o script redimensiona para o tamanho de treino (ex.: 256×256).
- **masks:** Máscara binária do telhado. Pixels de telhado = valor &gt; 0; fundo = 0. Mesmo nome base que a imagem (ex.: `tile_001.png`/`tile_001.png`) ou, no formato **chips**, `img_0.npy` com `mask_0.npy`, `img_1.npy` com `mask_1.npy`, etc. Formatos: PNG, TIF, **.npy**.

### Como obter as máscaras

- **Manual:** Desenhar em QGIS, ArcGIS ou outro GIS sobre a ortofoto; exportar como imagem binária.
- **Semi-automático:** Usar ferramentas de segmentação assistida (ex.: segmentação por diferença de elevação LIDAR, depois limpeza manual).
- **Conjuntos públicos:** Se existirem datasets de segmentação de telhados (ex.: competições ou projetos open-source), converter para o formato acima.

Recomenda-se incluir variedade: diferentes inclinações, materiais, sombras e claraboias/painéis (estes devem ficar **fora** da máscara, como no pós-processamento da API).

## Comando de treino

A partir da raiz do projeto:

**Script automático (cria/ativa .venv, instala e treina com `./chips`):**
```powershell
.\run_train.ps1
```
Em cmd: `run_train.bat`

**Manual:**
```bash
# Criar e ativar ambiente virtual (uma vez)
py -m venv .venv
.\.venv\Scripts\Activate.ps1   # PowerShell
pip install -e .

# Treino (ex.: dados em chips/)
python -m scripts.train_unet --data_dir ./chips --output ./models/unet_roof.pt --epochs 50
```

```bash
# Treino básico com pasta data/roof
python -m scripts.train_unet --data_dir ./data/roof --output ./models/unet_roof.pt

# Mais épocas e tamanho de patch
python -m scripts.train_unet --data_dir ./data/roof --output ./models/unet_roof.pt --epochs 100 --size 256 256

# Batch maior (requer mais GPU RAM)
python -m scripts.train_unet --data_dir ./data/roof --batch_size 16 --lr 5e-4
```

### Parâmetros principais

| Parâmetro     | Default   | Descrição |
|---------------|-----------|-----------|
| `--data_dir`  | (obrigatório) | Pasta raiz com subpastas de imagens e máscaras. |
| `--images`    | `images`  | Nome da subpasta com imagens RGB. |
| `--masks`     | `masks`   | Nome da subpasta com máscaras binárias. |
| `--output`    | `./models/unet_roof.pt` | Caminho do checkpoint a guardar (melhor validação). |
| `--size`      | `256 256` | Altura e largura dos patches de treino. |
| `--epochs`    | `50`      | Número de épocas. |
| `--batch_size`| `8`       | Tamanho do batch. |
| `--lr`        | `1e-3`    | Learning rate. |
| `--val_ratio` | `0.2`     | Fração dos dados para validação (0–1). |
| `--workers`   | `0`       | Workers do DataLoader. |
| `--seed`      | `42`      | Semente para reprodutibilidade. |

O script guarda sempre o modelo com **menor loss de validação**. O ficheiro `.pt` contém `state_dict` no formato esperado por `load_unet()` na API (incluindo a chave `"model"`).

## Usar o modelo treinado em produção

1. Copiar o ficheiro gerado (ex.: `models/unet_roof.pt`) para o servidor.
2. Definir a variável de ambiente (ou `.env`):
   ```env
   SEGMENTATION_MODEL_PATH=./models/unet_roof.pt
   ```
3. Reiniciar a API. A segmentação passará a usar o U-Net em vez do fallback heurístico.

## Dicas

- **Quantidade de dados:** Centenas de patches (ex.: 300–1000+) costumam dar resultados estáveis; mais dados melhoram robustez.
- **Balanceamento:** Se houver muito mais fundo do que telhado, considerar ponderação na loss (ex.: `pos_weight` em `BCEWithLogitsLoss`) ou aumentar ligeiramente o peso dos pixels de telhado.
- **Augmentation:** O script aplica apenas flip horizontal e vertical. Para mais variedade (rotação, brilho, etc.) pode estender-se `RoofDataset` em `roof_api/segmentation/dataset.py`.
- **GPU:** Com CUDA, o treino usa GPU automaticamente; caso contrário corre em CPU (mais lento).

## Modelo multiclasse (águas, claraboia, divisória, laje)

Para segmentar **só a área de telhado** (excluindo claraboia, lajes e divisórias) e reconhecer várias classes:

1. **Anotar no Label Studio** com as labels: `agua_a`, `agua_b`, `agua_c`, `claraboia`, `divisoria`, `laje`.
2. **Gerar chips multiclasse:**
   ```bash
   python -m scripts.label_studio_to_chips --export dados/export.json --images_dir ./dados --output_dir ./chips_multiclass --multiclass
   ```
3. **Treinar com 5 classes:**
   ```bash
   python -m scripts.train_unet --data_dir ./chips_multiclass --output ./models/unet_roof_multiclass.pt --num_classes 5 --epochs 50
   ```
4. **Configurar a API:** no `.env`: `SEGMENTATION_MODEL_PATH=./models/unet_roof_multiclass.pt` e `SEGMENTATION_NUM_CLASSES=5`.

A máscara usada para área e águas é **apenas a classe “água”** (1); claraboia, divisória e laje são reconhecidas mas excluídas da área.

**Importante:** Com poucos pares (ex.: 4–10), o modelo não generaliza bem: pode não identificar as duas águas, nem excluir claraboia, nem dar área correta. Para resultados aceitáveis, anote **dezenas a centenas** de imagens, incluindo telhados com duas águas, com claraboia e sem claraboia, e treine com mais épocas.

## Resolução 512×512 (igual à API)

A API obtém ortofoto **512×512** (Mapbox). Para o modelo “ver” a mesma escala em treino:

```bash
python -m scripts.train_unet --data_dir ./chips_multiclass --output ./models/unet_roof_multiclass.pt --num_classes 5 --size 512 512 --epochs 50
```

Treinar com `--size 512 512` pode melhorar a segmentação em produção quando a fonte de imagem for a mesma.
