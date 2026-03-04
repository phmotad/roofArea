# Integração RoofSense no Roof API

O [RoofSense](https://github.com/DimitrisMantas/RoofSense) é um dataset de segmentação semântica para **classificação de materiais de cobertura** (8 classes), com imagem aérea + LIDAR. Licença MIT. O que podemos aproveitar no nosso projeto e como usar o dataset deles.

---

## O que podemos usar do projeto deles

| Ideia / recurso | Uso no Roof API |
|-----------------|------------------|
| **Dataset (RGB + máscaras)** | **Sim.** Usar os **chips RGB** e converter as máscaras de 8 classes de material → **máscara binária** (telhado vs fundo) para **pré-treino** ou para aumentar variedade de dados (roof/chips). |
| **Classes de material (8)** | **Não direto.** O nosso modelo tem 5 classes **geométricas** (fundo, águas, claraboia, divisória, laje). As deles são materiais (membranas, gravilha, etc.). Não há mapeamento 1:1. Uso prático: tratar “qualquer material de telhado” = 1, resto = 0. |
| **Imagens multibanda (RGB + slope, nDRM, etc.)** | **Futuro.** O nosso DeepLabV3 usa só RGB. Se um dia quisermos entrada multibanda (ex.: + DSM/slope), o pipeline e normalização deles (ex.: `scales.bin`) são uma boa referência. Por agora, usamos só **RGB** do RoofSense. |
| **Tiled inference** | Já temos algo equivalente (crop por ponto). Podemos inspirar-nos na implementação deles se formos para áreas muito grandes. |
| **Estrutura dataset (splits, weights)** | Ideias para `splits.json`, pesos por classe, etc., ao organizar o nosso roof/. |

Resumo: o que nos interessa **agora** é o **dataset como fonte de pares RGB + máscara binária (telhado/fundo)** para pré-treino ou mais dados.

---

## Conseguimos o dataset deles para treinar o nosso modelo?

**Sim**, com duas ressalvas:

1. **Formato**  
   Eles disponibilizam (ou geram) imagens (RGB ou multibanda) e máscaras raster. Nós precisamos de **RGB** + **máscara binária** (telhado = 1, fundo = 0). Por isso é necessário um passo de **conversão**:  
   - Máscara deles: 8 classes de material + fundo (ex.: 0 = fundo, 1–8 = materiais).  
   - Nossa máscara: `mask_binary = (mask_raster > 0)` (tudo o que for telhado = 1).

2. **Onde está o dataset**  
   - **HuggingFace:** O README deles diz que o dataset pode ser obtido por “clone from HuggingFace Hub”. Vale verificar no repositório [DimitrisMantas/RoofSense](https://github.com/DimitrisMantas/RoofSense) e na página do [HuggingFace](https://huggingface.co/DimitrisMantas/RoofSense) a indicação exacta (link do dataset, se é `datasets` ou ficheiros num repo).  
   - **Gerar localmente:** O repositório deles permite gerar o dataset com `roofsense/main.py` (requer 3DBAG, etc.). Depois de gerado, podemos usar o nosso script para converter a pasta deles (images/ + masks/) para o nosso formato (roof/chips ou similar).

Ou seja: **conseguimos usar o dataset deles** desde que o tenhamos em disco (descarregado do HF ou gerado pelo código deles) e que o convertamos para **RGB + máscara binária**.

---

## Como usar no nosso pipeline

- **Pré-treino binário (roof/chips):**  
  Converter RoofSense → `images/` (só RGB) + `masks/` (binário: telhado=255, fundo=0). Colocar numa pasta (ex.: `roof/chips_roofsense`) e usar no notebook Kaggle como fonte extra de pré-treino, ou misturar com os teus chips existentes.

- **Não usar como multiclasse nosso:**  
  As 8 classes deles não correspondem às nossas 5 classes (águas, claraboia, divisória, laje, fundo). Usar só como **telhado vs fundo** evita confusão e mantém o nosso modelo geométrico.

O script `scripts/download_roofsense_dataset.py` (ver abaixo) faz o download (quando o dataset estiver disponível no HuggingFace) e a conversão para este formato.

---

## Citação

Se usares o dataset ou código deles:

```text
Mantas, D. (2024). CNN-based Roofing Material Segmentation using Aerial Imagery and LiDAR Data Fusion. 
Master's thesis, Delft University of Technology. 
https://resolver.tudelft.nl/uuid:c463e920-61e6-40c5-89e9-25354fadf549
```

---

## Resumo

- **O que usar:** Dataset deles como **RGB + máscara binária (telhado/fundo)** para pré-treino ou mais dados; ideias de pipeline (multibanda, tiled inference, splits) para evoluções futuras.  
- **Conseguir o dataset:** Sim — por download (HF) ou geração com o código deles; depois conversão com o nosso script para o formato roof/chips (binary masks).  
- **Treinar o nosso modelo:** Sim, como **dados adicionais de pré-treino** (telhado vs fundo), não como substituição das nossas 5 classes geométricas.
