# Ativar ambiente virtual, instalar projeto (se faltar) e treinar U-Net
# Executar na raiz do projeto: .\run_train.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv\Scripts\Activate.ps1)) {
    Write-Host "A criar ambiente virtual .venv ..."
    py -m venv .venv
}

Write-Host "A ativar .venv ..."
.\.venv\Scripts\Activate.ps1

Write-Host "A instalar dependencias (pip install -e .) ..."
pip install -e . -q

Write-Host "A treinar o modelo U-Net (chips -> models/unet_roof.pt) ..."
python -m scripts.train_unet --data_dir ./chips --output ./models/unet_roof.pt --epochs 50

Write-Host "Concluido. Modelo em ./models/unet_roof.pt"
