# Roof API — API Geoespacial para Análise de Telhados

API que, a partir de coordenadas (lat/lon), identifica o telhado, gera máscara, calcula área 3D e águas (inclinação/orientação), persiste em PostGIS e retorna JSON + imagem.

## Stack

- Python 3.10+
- FastAPI
- PostGIS / SQLAlchemy / GeoAlchemy2
- DeepLabV3+ (PyTorch) para segmentação
- Rasterio, GDAL, Shapely, GeoPandas
- PDAL (LIDAR), OpenCV, scikit-image

## Instalação

### Com Docker (recomendado)

```bash
docker compose up --build -d
```

API em http://localhost:8000. Ver [docs/docker.md](docs/docker.md).

### Local

```bash
pip install -e .
```

Configure variáveis de ambiente (ver `.env.example`) e execute:

```bash
uvicorn roof_api.main:app --reload
```

## Endpoint principal

`POST /telhado/analisar` — body: `{"lat": <float>, "lon": <float>}`

Documentação em `/docs` (OpenAPI).

## Documentação

- [Arquitetura (visão geral)](docs/arquitetura.md)
- [Arquitetura de produção](docs/arquitetura-producao.md) — pipeline canónico: imagem → DeepLabV3 → máscara → LIDAR → clustering → águas → área → PostGIS
- [Pipeline](docs/pipeline.md)
- [Exemplo API](docs/api-exemplo.md)
- [Fallback sem LIDAR](docs/fallback-lidar.md)
- [Performance e escalabilidade](docs/performance.md)
- [Treino do modelo (DeepLabV3+)](docs/treino-unet.md)
- [Fine-tuning com chips_segmentos (3 classes: fundo, linha, telhado)](docs/chips-segmentos-finetuning.md)
- [Integração RoofSense (dataset materiais de cobertura)](docs/roofsense-integracao.md)
- [Dataset AIRS no Kaggle (pré-treino binário)](docs/dataset-airs-kaggle.md)
- [Onde obter recursos (.env, ortofoto, LIDAR, modelo)](docs/onde-obter-recursos.md)
- [Rodar no Docker](docs/docker.md)

## Licença

MIT
