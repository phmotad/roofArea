# Variáveis de ambiente (.env)

Para saber **onde obter** cada recurso (base de dados, ortofoto, LIDAR, modelo), ver [onde-obter-recursos.md](onde-obter-recursos.md).

---

## Obrigatório para a API funcionar

Só isto é **estritamente necessário** para a API subir e conseguir responder a `POST /telhado/analisar`:

```env
# Base de dados (PostgreSQL com extensão PostGIS)
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/roof_db
```

- Substituir `USER`, `PASSWORD` e `HOST` pelos teus dados.
- O banco deve existir e ter a extensão PostGIS ativa (`CREATE EXTENSION postgis;`).
- Se não definires `DATABASE_URL`, o default é `postgresql+asyncpg://localhost/roof_db` (só funciona se o PostgreSQL estiver em localhost sem password).

---

## Opcionais (têm valor por defeito)

| Variável | Default | Uso |
|----------|---------|-----|
| `DATABASE_SYNC_URL` | `postgresql://localhost/roof_db` | Só para migrations Alembic (versão síncrona da URL). |
| `GEO_BUFFER_METERS` | `35` | Raio em metros em volta do ponto para recortar ortofoto e DSM. |
| `SEGMENTATION_MODEL_PATH` | `./models/unet_roof.pt` | Caminho do checkpoint U-Net. Se o ficheiro não existir, usa heurística. |
| `OUTPUT_IMAGE_BASE64` | `false` | Se `true`, a resposta JSON inclui a imagem em base64. |
| `CACHE_TTL_SECONDS` | `86400` (24h) | TTL do cache por coordenadas; `0` desativa. |
| `LOG_LEVEL` | `INFO` | Nível de log: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

---

## Opcionais (deixar vazio = fallback)

Se não estiverem definidas ou estiverem vazias, a API continua a funcionar com comportamento reduzido:

| Variável | Quando vazio | Quando preenchido |
|----------|-------------|-------------------|
| `MAPBOX_ACCESS_TOKEN` | — | Token Mapbox para usar **Mapbox Satellite** (Static API). Recomendado. |
| `ORTHO_TILE_URL` | Usado se Mapbox não estiver definido. | URL que devolva PNG da área; ou vazio = placeholder. |
| `LIDAR_DGT_PATH` | Não usa DSM Portugal. | Caminho (ou URL) do raster DSM DGT. |
| `LIDAR_PNOA_PATH` | Não usa DSM Espanha. | Caminho (ou URL) do raster DSM PNOA. |

Sem ortofoto real: a análise corre, mas a imagem de saída é placeholder.  
Sem LIDAR: inclinação/azimute ficam a zero e `fonte_lidar` vem `null` na resposta.

---

## Exemplo mínimo (.env)

Só para a API responder (com placeholder de ortofoto e sem LIDAR):

```env
DATABASE_URL=postgresql+asyncpg://postgres:minhasenha@localhost:5432/roof_db
```

## Exemplo completo (.env)

Para uso com ortofoto, LIDAR e modelo treinado:

```env
DATABASE_URL=postgresql+asyncpg://postgres:minhasenha@localhost:5432/roof_db
DATABASE_SYNC_URL=postgresql://postgres:minhasenha@localhost:5432/roof_db

GEO_BUFFER_METERS=35
ORTHO_TILE_URL=https://exemplo.com/wmts/ortofoto
LIDAR_DGT_PATH=/dados/dsm/dgt_portugal.tif
LIDAR_PNOA_PATH=

SEGMENTATION_MODEL_PATH=./models/unet_roof.pt
OUTPUT_IMAGE_BASE64=false
CACHE_TTL_SECONDS=86400
LOG_LEVEL=INFO
```

Copiar de `.env.example` e ajustar apenas o que precisares.
