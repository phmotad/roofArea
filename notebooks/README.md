# Notebook Colab — treino U-Net com GPU

## Ficheiro

- **`colab_train_roof_unet.ipynb`** — pré-treino (Inria) + fine-tuning (chips multiclasse) na GPU do Colab.

## Como usar

1. **No Colab (browser)**  
   - Abre o ficheiro no [Google Colab](https://colab.research.google.com) (Upload do `colab_train_roof_unet.ipynb`).  
   - **Runtime → Change runtime type → GPU** (T4 ou superior).  
   - **Projeto no GitHub:** na célula do clone, cola o URL do teu repo e substitui `TEU_USER` pelo teu username (ex.: `https://github.com/joao/roofArea.git`).

2. **Na extensão Colab do Cursor**  
   - Abre `colab_train_roof_unet.ipynb` no Cursor e corre no Colab. O projeto já está no ambiente; não é necessário clone.

3. **Dados para fine-tuning (teus chips)**  
   - Na pasta do projeto (no PC), cria um zip da pasta `chips_multiclass`:
     ```bash
     # PowerShell (na raiz do projeto)
     Compress-Archive -Path .\chips_multiclass -DestinationPath chips_multiclass.zip
     ```
   - No notebook, na célula "Upload dos teus chips", faz upload de `chips_multiclass.zip`.  
   - O zip deve conter a pasta `chips_multiclass` com `images/` e `masks/` lá dentro (resultado de `label_studio_to_chips --multiclass`).

4. **Correr todas as células**  
   - O notebook descarrega o Inria, faz pré-treino, depois fine-tuning com os teus chips, **corre o teste** (imagem do telhado + área estimada) e permite descarregar `unet_roof_multiclass.pt`.

## Regenerar chips_multiclass a partir do Label Studio

Se exportaste novas anotações (ex.: `project-1-at-2026-02-25-00-35-7a9fdfa6.json`) e tens as imagens numa pasta (ex.: `dados_completo`), regenera a pasta de treino:

```powershell
python -m scripts.label_studio_to_chips --export project-1-at-2026-02-25-00-35-7a9fdfa6.json --images_dir dados_completo --output_dir chips_multiclass --multiclass
```

A pasta `dados_completo` deve conter as imagens com os nomes referenciados no export (ex.: `casas.png`, `tile_006.png`, …).

## Nota sobre TPU

O notebook está preparado para **GPU** (CUDA). Para usar TPU no Colab seria preciso `torch_xla` e adaptar o código; para este modelo, a GPU é a opção mais simples e habitual.
