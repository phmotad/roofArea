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

**Reiniciar só a API** (útil após alterar o `.env` ou modelos):
```bash
docker compose restart api
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
| **api** | roof-api    | 8000  | API FastAPI. Faz `alembic upgrade head` e depois inicia o uvicorn. Monta `./lidar` e `./models` (DeepLabV3: `deeplabv3_roof_multiclass.pt`, opcionalmente `unet_lines.pt`). |

A API fica em **http://localhost:8000**. Documentação: **http://localhost:8000/docs**.

## Variáveis no Docker

O `docker-compose.yml` define automaticamente:

- `DATABASE_URL` e `DATABASE_SYNC_URL` com o host **db** (rede interna).
- `LIDAR_DGT_PATH` e `LIDAR_PNOA_PATH` = **/app/lidar** (pasta montada a partir de `./lidar` no host).

O resto (por exemplo `MAPBOX_ACCESS_TOKEN`) vem do teu **`.env`**.

## Modelos (pasta `./models`)

A pasta **`./models`** é montada em **/app/models** no container. Para a API usar segmentação (e não a máscara heurística), precisas de:

- `models/deeplabv3_roof_multiclass.pt` (obrigatório — modelo principal DeepLabV3+)
- `models/unet_lines.pt` (opcional — modelo de linhas U-Net)

**Verificar se o container vê os ficheiros:**
```bash
docker compose exec api ls -la /app/models
```

Se aparecer "Segmentação: modelo não encontrado" nos logs da API, confirma que `deeplabv3_roof_multiclass.pt` existe em `./models` e reinicia: `docker compose restart api`.

## Pasta `lidar`

A pasta **`./lidar`** do projeto é montada em **/app/lidar** dentro do container. Coloca aí os ficheiros `.tif` da DGT/PNOA. Se `lidar` não existir, o Docker cria um diretório vazio e a API corre sem DSM até lá colocares os TIFFs.

## Ficheiros

- **`Dockerfile`** – imagem da API (Python 3.12, instala o projeto e sobe uvicorn).
- **`docker-compose.yml`** – orquestra os serviços `db` e `api`.
- **`docker/init-db/01-postgis.sql`** – ativa a extensão PostGIS na base `roof_db` na primeira execução.
