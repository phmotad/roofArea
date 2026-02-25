# Rodar o projeto no Docker (Docker Desktop)

O projeto sobe com **dois containers**: PostgreSQL+PostGIS (base de dados) e a API Roof.

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e em execução.
- Ficheiro **`.env`** na raiz do projeto (cópia do `.env.example` com valores preenchidos).
- Pasta **`lidar`** na raiz com os GeoTIFFs (ou o caminho que tiveres em `LIDAR_DGT_PATH`/`LIDAR_PNOA_PATH` será sobrescrito no Docker por `/app/lidar`).

## Comandos

**Construir e subir (em background):**
```bash
docker compose up --build -d
```

**Ver logs:**
```bash
docker compose logs -f api
```

**Parar:**
```bash
docker compose down
```

**Parar e apagar o volume da base de dados:**
```bash
docker compose down -v
```

## O que sobe

| Serviço | Container   | Porta | Descrição |
|---------|-------------|-------|-----------|
| **db**  | roof-db     | 5432  | PostgreSQL 16 + PostGIS. Dados em volume `roof-db-data`. |
| **api** | roof-api    | 8000  | API FastAPI. Faz `alembic upgrade head` e depois inicia o uvicorn. Monta `./lidar` e `./models` (modelo U-Net em `./models/unet_roof.pt`). |

A API fica em **http://localhost:8000**. Documentação: **http://localhost:8000/docs**.

## Variáveis no Docker

O `docker-compose.yml` define automaticamente:

- `DATABASE_URL` e `DATABASE_SYNC_URL` com o host **db** (rede interna).
- `LIDAR_DGT_PATH` e `LIDAR_PNOA_PATH` = **/app/lidar** (pasta montada a partir de `./lidar` no host).

O resto (por exemplo `MAPBOX_ACCESS_TOKEN`) vem do teu **`.env`**.

## Pasta `lidar`

A pasta **`./lidar`** do projeto é montada em **/app/lidar** dentro do container. Coloca aí os ficheiros `.tif` da DGT/PNOA. Se `lidar` não existir, o Docker cria um diretório vazio e a API corre sem DSM até lá colocares os TIFFs.
