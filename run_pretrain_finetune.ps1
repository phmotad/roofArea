# Pre-treino (Inria binario) + fine-tuning (chips multiclasse)
# Executar na raiz do projeto: .\run_pretrain_finetune.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv\Scripts\Activate.ps1)) {
    Write-Host "A criar ambiente virtual .venv ..."
    py -m venv .venv
}

.\.venv\Scripts\Activate.ps1
pip install -e . -q

$inriaImages = Get-ChildItem .\dados_inria\images -Filter *.png -ErrorAction SilentlyContinue
if ($inriaImages.Count -eq 0) {
    Write-Host "dados_inria vazio. A descarregar Inria ..."
    pip install huggingface_hub -q 2>$null
    python -m scripts.download_inria_dataset --output_dir ./dados_inria
    if ((Get-ChildItem .\dados_inria\images -Filter *.png -ErrorAction SilentlyContinue).Count -eq 0) {
        Write-Host "ERRO: Nao foi possivel obter patches Inria. Tente executar manualmente:"
        Write-Host "  python -m scripts.download_inria_dataset --output_dir ./dados_inria"
        exit 1
    }
}

$device = if (python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>$null) { "cuda" } else { "cpu" }
Write-Host "Device: $device"

New-Item -ItemType Directory -Force -Path .\models | Out-Null

Write-Host ""
Write-Host "=== Pre-treino (binario, Inria) ==="
$env:PYTHONUNBUFFERED = "1"
python -u -m scripts.train_unet `
    --data_dir ./dados_inria `
    --output ./models/unet_roof_pretrain.pt `
    --num_classes 1 `
    --size 512 512 `
    --epochs 30 `
    --device $device

Write-Host ""
Write-Host "=== Fine-tuning (multiclasse, chips) ==="
python -u -m scripts.train_unet `
    --data_dir ./chips_multiclass `
    --output ./models/unet_roof_multiclass.pt `
    --num_classes 5 `
    --size 512 512 `
    --epochs 50 `
    --pretrain ./models/unet_roof_pretrain.pt `
    --device $device

Write-Host ""
Write-Host "Concluido. Modelo final: .\models\unet_roof_multiclass.pt"
