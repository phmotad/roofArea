# roof/archive — Estrutura AIRS (Kaggle)

Esta pasta segue a **estrutura do dataset AIRS** no Kaggle ([Aerial Imagery for Roof Segmentation](https://www.kaggle.com/datasets/atilol/aerialimageryforroofsegmentation)):

```
archive/
  train/
    image/   ← imagens .tif
    label/   ← máscaras .tif (mesmo nome que a imagem)
  val/
    image/
    label/
  test/
    image/
    label/
```

- **No Kaggle:** o dataset fica em `/kaggle/input/aerialimageryforroofsegmentation/` com essa mesma árvore.
- **Localmente:** ao descarregar o dataset do Kaggle, extrair aqui de forma a ter `roof/archive/train/image/*.tif`, `roof/archive/train/label/*.tif`, e o mesmo para `val` e `test`.

Os ficheiros `train.txt` e `val.txt` são listas de referência (nomes de ficheiros do split original); o pipeline usa as pastas `train/image`, `train/label`, etc.

Contagens típicas do AIRS: train 857 imagens, val 94, test 95 (máscaras com o mesmo nome em `label/`).
