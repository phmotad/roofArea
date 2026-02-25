# Treino U-Net apenas com os dados do Label Studio (chips_dados: 4 imagens, só águas a/b/c). GPU.
# Executar na raiz do projeto: .\run_train_label_studio.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv\Scripts\Activate.ps1)) {
    Write-Host "A criar ambiente virtual .venv ..."
    py -m venv .venv
}

.\.venv\Scripts\Activate.ps1
pip install -e . -q

if (-not (Test-Path chips_dados\images) -or -not (Test-Path chips_dados\masks)) {
    Write-Host "A gerar chips_dados a partir do export do Label Studio (só aguas a, b, c) ..."
    python -m scripts.label_studio_to_chips --export "dados\project-1-at-2026-02-19-00-25-bf5f8422.json" --images_dir "dados" --output_dir "chips_dados" --labels "agua_a,agua_b,agua_c"
}

Write-Host "A treinar na GPU (apenas chips_dados) ..."
python -m scripts.train_unet --data_dir ./chips_dados --output ./models/unet_roof.pt --epochs 80 --val_ratio 0.25 --batch_size 2 --device cuda

Write-Host "Concluido. Modelo em ./models/unet_roof.pt"
