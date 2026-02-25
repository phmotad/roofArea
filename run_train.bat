@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
    echo A criar ambiente virtual .venv ...
    py -m venv .venv
)
call .venv\Scripts\activate.bat
echo A instalar dependencias ...
pip install -e . -q
echo A treinar o modelo U-Net ...
python -m scripts.train_unet --data_dir ./chips --output ./models/unet_roof.pt --epochs 50
echo Concluido. Modelo em ./models/unet_roof.pt
pause
