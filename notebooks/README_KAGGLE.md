# Treino U-Net no Kaggle (passo a passo)

Usar o Kaggle para pré-treino (Inria) + fine-tuning (chips multiclasse) com GPU gratuita.

---

## Importar o notebook pronto (tudo automático)

1. Abre [Kaggle](https://www.kaggle.com) → **Code → New Notebook**.
2. **File → Import Notebook** → **Upload** → seleciona **`kaggle_train_roof_unet.ipynb`** (em `notebooks/`).
3. **Settings:** Accelerator **GPU** | **Internet** On.
4. **Add data:** anexa os datasets (obrigatório: **roof-chips-multiclass**; opcionais: **roof-inria-patches**, **roof-roofsat**).
5. **Run All** — não precisas de editar nada: os caminhos são detetados sozinhos; o pré-treino corre para Inria e/ou RoofSat se anexados; o fine-tuning usa o melhor checkpoint disponível.

---

## Se só aparecer CPU (sem opção GPU)

No Kaggle, a **GPU só fica disponível** se:

1. **Verificação por telemóvel** — Na conta Kaggle: **Settings → Phone verification**. Sem verificação, o Accelerator fica só com **None** (CPU).
2. **Quota semanal** — Na conta gratuita há um limite de horas de GPU por semana (ex.: 30 h). Quando esgota, o dropdown pode mostrar só CPU até à semana seguinte.
3. **Escolher GPU ao criar o notebook** — No painel direito: **Settings → Accelerator → GPU T4 x2** (ou P100). Se não vires "GPU", verifica o ponto 1.

**Se só tiveres CPU:** o notebook corre na mesma, mas o treino fica muito mais lento (horas em vez de minutos). Podes reduzir épocas nas células de treino (ex.: `--epochs 5`) para testar.

---

## Passo 1: Preparar os dados e gerar os zips

Tens três fontes de dados no projeto:

| Diretório | Uso no Kaggle | Zip gerado |
|-----------|----------------|------------|
| `dados_inria/images/` + `dados_inria/masks/` | Pré-treino (Inria) | `roof-inria-patches.zip` |
| `chips_multiclass/` | Fine-tuning (multiclasse) | `roof-chips-multiclass.zip` |
| `dados_inria/Roofsat/` | Opcional (outro formato) | `roof-roofsat.zip` |

**Não precisas de compactar à mão.** Na raiz do projeto, corre:

```powershell
python -m scripts.prepare_kaggle_zips
```

Os zips são criados na pasta `zips_kaggle/`. Se quiseres noutro sítio:

```powershell
python -m scripts.prepare_kaggle_zips --output_dir .\meus_zips
```

Requisitos: `dados_inria` deve ter `images/` e `masks/` (patches Inria). Se ainda não tiveres, corre primeiro:

```powershell
python -m scripts.download_inria_dataset --output_dir dados_inria
```

O script **não** inclui a pasta Roofsat dentro do zip do Inria; o zip do Inria tem só `images/` e `masks/` na raiz, como o notebook espera.

---

## Passo 2: Criar os datasets no Kaggle

1. Entra em [kaggle.com](https://www.kaggle.com) e faz login.
2. **Datasets → New Dataset**.
3. Para cada zip em `zips_kaggle/`:
   - **roof-inria-patches.zip** → nome do dataset: `roof-inria-patches` (pré-treino).
   - **roof-chips-multiclass.zip** → nome do dataset: `roof-chips-multiclass` (fine-tuning).
   - **roof-roofsat.zip** → nome do dataset: `roof-roofsat` (opcional; pré-treino RoofSat).
4. Faz upload do zip e **Create** / **Save**.

Recomenda-se usar os **nomes** `roof-chips-multiclass`, `roof-inria-patches` e `roof-roofsat` para o notebook os encontrar automaticamente. Se usares outros nomes, o notebook tenta detetar por estrutura (pastas `images/`+`masks/`, `chips_multiclass/`, `building_masks`+`train.txt`).

---

## Passo 3: Criar o notebook no Kaggle

1. **Code → New Notebook**.
2. **Settings** (painel direito):  
   - **Accelerator:** GPU (P100 ou T4).  
   - **Internet:** On (para clone do GitHub e eventual download do Inria).
3. Guarda o notebook (ex.: `roof-unet-train`).

---

## Passo 4: Anexar os datasets ao notebook

1. No painel direito, em **Input** (ou **Add data**), clica **Add input**.
2. Procura o teu dataset (ex.: `roof-chips-multiclass`) e adiciona.
3. Se criaste dataset do Inria, adiciona também.
4. O notebook deteta automaticamente os datasets em `/kaggle/input/` (por nome ou por estrutura). Não é preciso alterar variáveis.

---

## Passo 5: Células do notebook

Copia o conteúdo das secções abaixo para células no notebook, por ordem.

### Célula 1 – Verificar GPU

```python
import subprocess
out = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'], capture_output=True, text=True)
print('GPU:', out.stdout.strip() if out.returncode == 0 else 'Nenhuma GPU')
```

### Célula 2 – Clone do repositório

```python
import os
REPO_URL = "https://github.com/phmotad/roofArea.git"
REPO_DIR = "roofArea"

if os.path.isdir(REPO_DIR) and os.path.isfile(os.path.join(REPO_DIR, "scripts", "train_unet.py")):
    print("Projeto já presente.")
else:
    !git clone --depth 1 {REPO_URL}
%cd roofArea
```

### Célula 3 – Instalar dependências

```python
!pip install -q torch torchvision --index-url https://download.pytorch.org/whl/cu121
!pip install -q pillow numpy opencv-python-headless scikit-image huggingface_hub
!pip install -q -e .
```

### Célula 4 – Definir caminhos (ajusta aos teus datasets)

```python
# Ajusta os nomes aos slugs dos teus datasets no Kaggle
import os
KAGGLE_INPUT = "/kaggle/input"

# Chips para fine-tuning (obrigatório)
CHIPS_PATH = os.path.join(KAGGLE_INPUT, "roof-chips-multiclass", "chips_multiclass")  # ou "chips_multiclass" se a raiz do dataset for essa pasta
if not os.path.isdir(CHIPS_PATH):
    CHIPS_PATH = os.path.join(KAGGLE_INPUT, "roof-chips-multiclass")  # raiz do dataset
print("Chips:", CHIPS_PATH, "→ existe:", os.path.isdir(CHIPS_PATH))

# Inria: usar dataset anexado OU descarregar do Hugging Face
INRIA_PATH = "/kaggle/working/dados_inria"
if os.path.isdir(os.path.join(KAGGLE_INPUT, "roof-inria-patches")):
    INRIA_PATH = os.path.join(KAGGLE_INPUT, "roof-inria-patches")
    if os.path.isdir(os.path.join(INRIA_PATH, "dados_inria")):
        INRIA_PATH = os.path.join(INRIA_PATH, "dados_inria")
    print("Inria: usar dataset anexado →", INRIA_PATH)
else:
    print("Inria: será descarregado para", INRIA_PATH)
```

### Célula 5 – Descarregar Inria (só se não anexaste dataset Inria)

```python
# Correr apenas se não tens dataset Inria anexado
import os
if "kaggle/working" in INRIA_PATH or not os.path.isdir(os.path.join(INRIA_PATH, "images")):
    !python -m scripts.download_inria_dataset --output_dir {INRIA_PATH}
else:
    print("Inria já disponível em", INRIA_PATH)
```

### Célula 6 – Pré-treino (binário, Inria)

```python
import subprocess
import os
os.makedirs("/kaggle/working/models", exist_ok=True)
subprocess.run([
    "python", "-u", "-m", "scripts.train_unet",
    "--data_dir", INRIA_PATH,
    "--output", "/kaggle/working/models/unet_roof_pretrain.pt",
    "--num_classes", "1", "--size", "512", "512", "--epochs", "30", "--device", "cuda"
], check=True)
```

### Célula 7 – Fine-tuning (multiclasse, teus chips)

```python
subprocess.run([
    "python", "-u", "-m", "scripts.train_unet",
    "--data_dir", CHIPS_PATH,
    "--output", "/kaggle/working/models/unet_roof_multiclass.pt",
    "--num_classes", "5", "--size", "512", "512", "--epochs", "30", "--device", "cuda",
    "--pretrain", "/kaggle/working/models/unet_roof_pretrain.pt"
], check=True)
```

### Célula 8 – (Opcional) Teste rápido

```python
from pathlib import Path
import sys
sys.path.insert(0, '.')
from roof_api.segmentation.unet_model import load_unet
model, _ = load_unet('/kaggle/working/models/unet_roof_multiclass.pt', num_classes=5)
model.eval()
img_dir = Path(CHIPS_PATH) / 'images'
imgs = list(img_dir.glob('*.png'))[:1]
print('Modelo carregado. Imagens em', img_dir, ':', len(imgs))
```

---

## Passo 6: Correr o notebook e guardar o modelo

1. **Run All** (ou corre célula a célula).
2. Os ficheiros em `/kaggle/working/` são guardados com o notebook quando fazes **Save Version** (canto superior direito) e marcas **Save output** (ou equivalente). Assim o modelo (ex.: `unet_roof_multiclass.pt`) fica associado à versão.
3. Para descarregar o modelo para o teu PC:  
   - Abre a versão guardada do notebook → painel **Output** → descarrega o ficheiro `.pt`, ou  
   - No próprio notebook, no fim, podes usar:
   ```python
   from IPython.display import FileLink
   FileLink(r'/kaggle/working/models/unet_roof_multiclass.pt', result_html_prefix='Download modelo: ')
   ```
   (se o Kaggle permitir download directo do working dir na UI).

---

## Resumo rápido

| Passo | O que fazer |
|-------|-------------|
| 1 | No PC: criar `chips_multiclass.zip` (e opcionalmente zip do Inria). |
| 2 | Kaggle: criar 1 ou 2 datasets e fazer upload. |
| 3 | Kaggle: novo notebook, GPU On, Internet On. |
| 4 | Anexar os datasets ao notebook. |
| 5 | Colar as células (clone, pip, paths, Inria se necessário, pré-treino, fine-tuning). |
| 6 | Run All → Save Version (com output) → descarregar o `.pt`. |

Se os nomes dos teus datasets forem diferentes, altera em **Célula 4** as variáveis `CHIPS_PATH` e (se usares) o caminho do Inria anexado.
