# Treino do U-Net com dados do Label Studio

Se anotaste polígonos no **Label Studio** (águas, calaboia, divisória, lajes, etc.), podes converter a exportação para o formato do projeto e treinar o modelo.

## 1. Exportar do Label Studio

1. No projeto, vai a **Export** e escolhe **JSON** (ou **JSON_MIN**).
2. Guarda o ficheiro (ex.: `label_studio_export.json`).
3. As imagens que importaste no Label Studio têm de estar numa pasta no teu PC com os **mesmos nomes** que aparecem no export (ex.: se no JSON está `"image": "telhado_001.png"`, o ficheiro deve existir nessa pasta).

## 2. Estrutura esperada

- **Pasta das imagens:** contém as imagens RGB (PNG, JPG, etc.) com os mesmos nomes que no export.
- **Export JSON:** lista de tasks; cada task tem `data.image` (nome ou URL da imagem) e `annotations[].result` com regiões do tipo **polygon** / **polygonlabels** (`value.points` em percentagem 0–100, `value.polygonlabels`).

## 3. Converter para o dataset de treino

Na raiz do projeto:

```powershell
# Todas as etiquetas de polígono contam como "telhado" (máscara binária)
python -m scripts.label_studio_to_chips --export "C:\caminho\label_studio_export.json" --images_dir "C:\caminho\minhas_imagens" --output_dir ./chips

# Só algumas etiquetas (ex.: águas, lajes, calaboia, a, b, e, divisória)
python -m scripts.label_studio_to_chips --export "C:\caminho\label_studio_export.json" --images_dir "C:\caminho\minhas_imagens" --output_dir ./chips --labels "aguas,lajes,calaboia,a,b,e,divisoria"
```

Isto cria:

- `chips/images/` – cópias das imagens com nomes estáveis
- `chips/masks/` – máscaras binárias (255 = telhado, 0 = resto) em PNG

As etiquetas em `--labels` são normalizadas (minúsculas, espaços → `_`). Usa os nomes exactos das tuas labels no Label Studio (ex.: "águas" → `aguas`).

## 4. Treinar o modelo

Depois de gerar `chips/`:

```powershell
.\run_train.ps1
```

ou:

```powershell
python -m scripts.train_unet --data_dir ./chips --output ./models/unet_roof.pt --epochs 50
```

O modelo guardado em `./models/unet_roof.pt` é o que a API usa com `SEGMENTATION_MODEL_PATH`.

## Resumo do fluxo

| Passo | O que fazer |
|-------|-------------|
| 1 | Anotar no Label Studio (polygon segmentation): águas, calaboia, divisória, lajes, etc. |
| 2 | Export → JSON; guardar o ficheiro. |
| 3 | Ter as imagens numa pasta (mesmos nomes que no export). |
| 4 | `python -m scripts.label_studio_to_chips --export ... --images_dir ... --output_dir ./chips [--labels ...]` |
| 5 | `python -m scripts.train_unet --data_dir ./chips --output ./models/unet_roof.pt` |
| 6 | Configurar a API com `SEGMENTATION_MODEL_PATH=./models/unet_roof.pt`. |

## Como me enviar os dados para treinar

Para eu (ou outra pessoa) treinar por ti:

1. **Export do Label Studio:** envia o ficheiro JSON da exportação (Export → JSON).
2. **Imagens:** envia a pasta com as imagens de telhado (os ficheiros que estão no projeto do Label Studio), com os mesmos nomes que aparecem no campo `image` do JSON.
3. (Opcional) Lista de labels a usar como “telhado”, por exemplo: `aguas, lajes, calaboia, a, b, e, divisoria`.

Com o JSON + pasta de imagens no mesmo layout (nomes iguais ao export), quem treina pode correr:

```bash
python -m scripts.label_studio_to_chips --export label_studio_export.json --images_dir ./minhas_imagens --output_dir ./chips --labels "aguas,lajes,calaboia,a,b,e,divisoria"
python -m scripts.train_unet --data_dir ./chips --output ./models/unet_roof.pt --epochs 50
```

Se preferires que **todas** as regiões poligonais contem como telhado, omite o `--labels` na conversão.
