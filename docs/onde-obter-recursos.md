# Onde obter os recursos (base de dados, imagem de base, LIDAR, modelo)

Resumo de onde conseguir cada recurso referido no `.env`.

---

## 1. PostgreSQL + PostGIS (DATABASE_URL)

**O que é:** Base de dados com extensão espacial para guardar telhados e águas.

**Opções:**

| Opção | Como obter |
|-------|------------|
| **Local** | Instalar [PostgreSQL](https://www.postgresql.org/download/) e depois a extensão PostGIS (`CREATE EXTENSION postgis;`). No Windows: [EDB](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads) ou [PostGIS Windows](https://postgis.net/windows_downloads/). |
| **Docker** | `docker run -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgis/postgis:16-3.4` (imagem já com PostGIS). Depois criar a base: `createdb -U postgres roof_db` e dentro dela `CREATE EXTENSION postgis;`. |
| **Cloud** | Serviços com PostGIS: [Neon](https://neon.tech), [Supabase](https://supabase.com), [Aiven](https://aiven.io/postgresql), [AWS RDS](https://aws.amazon.com/rds/) (ativar PostGIS no parâmetro). |

**Exemplo .env (Docker local):**
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/roof_db
DATABASE_SYNC_URL=postgresql://postgres:postgres@localhost:5432/roof_db
```

---

## 2. Imagem de base (ORTHO_TILE_URL)

**Precisa de ser ortofoto?** Não. Pode ser **ortofoto, imagens de satélite (Sentinel-2, Planet, Maxar, etc.) ou qualquer imagem georreferenciada** em que os telhados sejam visíveis. O pipeline só precisa de: (1) uma imagem RGB que cubra a área do ponto; (2) os bounds (minx, miny, maxx, maxy) em WGS84 que correspondam a essa imagem, para o cálculo de áreas em m². O ideal é que a imagem esteja **ortorretificada** (escala uniforme), para as áreas calculadas serem coerentes; a maioria das imagens de satélite e ortofotos oficiais já o são.

**O que é:** URL que devolve uma imagem da área (ou vazio = placeholder). A variável mantém o nome `ORTHO_TILE_URL` por compatibilidade.

**Fontes possíveis:**

- **Ortofotos** (DGT, IGN): ver abaixo.
- **Satélite:** Sentinel-2 (ESA), Planet, Maxar, etc. — normalmente já georreferenciadas; basta um serviço que, dado (lat, lon) ou bbox, devolva o PNG.

**Portugal (DGT – ortofotos):**

- Serviços **WMS/WMTS** para visualização (não download direto de tiles por URL única).
- Documentação e URLs: [DGT – Ortofotos](https://www.dgterritorio.gov.pt/cartografia/cartografia-topografica/ortofotos/ortofotos-digitais).
- WMTS 2021 (exemplo GetCapabilities):  
  `https://cartografia.dgterritorio.gov.pt/ortos2021/service?service=WMTS&REQUEST=GetCapabilities&VERSION=1.3.0`
- Para usar na API é preciso um **proxy ou serviço** que, a partir de (lat, lon) ou bbox, chame o WMS/WMTS e devolva uma imagem. O `.env` espera uma URL que devolva PNG (ex.: um microserviço teu que faça esse pedido ao WMTS). Alternativa: usar outro fornecedor de tiles (ex.: OpenStreetMap como fallback visual).

**Espanha (IGN – ortofotos PNOA):**

- **WMS:** `https://www.ign.es/wms-inspire/pnoa-ma`  
  GetCapabilities: `https://www.ign.es/wms-inspire/pnoa-ma?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0`
- **WMTS:** `https://www.ign.es/wmts/pnoa-ma`
- Também é serviço de visualização; para uma URL “direta” de tile na API seria necessário um proxy que converta (lat, lon) ou bbox em pedido WMS/WMTS e devolva PNG.

**Resumo:** O campo `ORTHO_TILE_URL` no projeto está pensado para uma URL que devolva uma imagem (ex.: `https://teu-servidor/tile?lat=38.7&lon=-9.1`). Os serviços oficiais são WMS/WMTS; para os usar tens de implementar um pequeno serviço que, dado o ponto ou bbox, chame o WMS/WMTS e devolva o PNG, e colocar *essa* URL no `.env`. Se não tiveres isso, deixar vazio e a API usa placeholder.

### Onde arranjar fotos gratuitas e atualizadas com resolução boa para telhados

| Fonte | Resolução | Atualização | Cobertura | Acesso | Notas |
|-------|-----------|-------------|-----------|--------|--------|
| **Ortofotos DGT (PT)** | **25 cm** | 2018/2021 | Portugal continental | WMS/WMTS (precisas de proxy) | Melhor resolução gratuita em PT. [DGT Ortofotos](https://www.dgterritorio.gov.pt/cartografia/cartografia-topografica/ortofotos/ortofotos-digitais). |
| **Ortofotos PNOA (ES)** | **25–50 cm** | Anual | Espanha | WMS/WMTS (precisas de proxy) | Melhor resolução gratuita em ES. [IGN WMS PNOA](https://www.ign.es/wms-inspire/pnoa-ma). |
| **Sentinel-2 (Copernicus)** | **10 m** | ~5 dias | Global | Gratuito com registo; WMTS/WMS | Resolução limitada (telhados grandes visíveis; pequenos = poucos pixels). [Copernicus Data Space](https://dataspace.copernicus.eu/) → registo → Sentinel Hub API. |
| **OpenAerialMap** | **Variável (até &lt;1 m)** | Variável | Pontual (comunidade) | Gratuito, sem conta | Imagens de UAV e satélite abertas; cobertura irregular (não cobre todo PT/ES). [map.openaerialmap.org](https://map.openaerialmap.org/) e [API](https://docs.openaerialmap.org/api/api/). |
| **Mapbox Satellite** | **0,3–1 m** (zoom alto) | Atualizada | Global (melhor em certas regiões) | **Free tier** (token) | Boa resolução; limite de requests no plano gratuito. [Mapbox](https://www.mapbox.com/). **Integrado neste projeto:** define `MAPBOX_ACCESS_TOKEN` no `.env`. |

**Recomendações:**

- **Portugal / Espanha, melhor qualidade gratuita:** Ortofotos oficiais (DGT e IGN). Resolução 25–50 cm é suficiente para ver telhados com pormenor. O acesso é por WMS/WMTS: é preciso um pequeno proxy que, dado (lat, lon) ou bbox, chame GetMap/GetTile e devolva PNG — essa URL é a que colocas em `ORTHO_TILE_URL`.
- **Rápido e global, sem implementar proxy:** **Sentinel-2** via [Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu/) (registo gratuito). Resolução 10 m: telhados grandes ficam visíveis; para telhados pequenos a precisão é limitada.
- **Onde existir cobertura:** **OpenAerialMap** pode ter imagens muito boas (UAV); verificar no [mapa](https://map.openaerialmap.org/) se a tua zona tem imagens e usar a API para integrar.

Nenhuma destas fontes é uma “URL de tile única” que possas colocar diretamente no `.env`: ou usas um proxy teu (WMS/WMTS → PNG) ou integras a API Copernicus/Mapbox/OAM no teu código de aquisição de imagem. **Mapbox** está já integrado: define `MAPBOX_ACCESS_TOKEN` no `.env` (token em [account.mapbox.com](https://account.mapbox.com/)) e a API usa a Static Images API para obter a imagem da área.

---

## 3. LIDAR / DSM (LIDAR_DGT_PATH, LIDAR_PNOA_PATH)

**O que é:** Modelos digitais de superfície (DSM) em raster (ex.: GeoTIFF) para calcular inclinação e orientação reais. São **ficheiros no disco** que a API abre com Rasterio. No `.env` indicas o **caminho do ficheiro** (ex.: `C:/dados/dsm_dgt.tif`). Se as variáveis estiverem vazias, a API corre sem LIDAR (`fonte_lidar = null`).

---

### Como obter DGT LIDAR (Portugal)

1. **Entrar no portal**
   - Abre [Centro de Dados DGT – Downloads](https://cdd.dgterritorio.gov.pt/dgt-fe/downloads) (pode ser preciso criar conta/login, consoante o tipo de dado).

2. **Escolher o produto**
   - Procura o **Levantamento LIDAR** ou **Modelo Digital de Superfície (DSM)**.
   - Estão disponíveis GeoTIFF em **50 cm** e **2 m** de resolução. Para telhados, 50 cm ou 2 m servem (2 m é mais leve).

3. **Selecionar a área**
   - Define a área de interesse (por mapa, por concelho, ou por coordenadas). O limite por sessão é cerca de **200 km²**; para mais área pode ser preciso fazer vários pedidos ou contactar a DGT.

4. **Adicionar ao carrinho e descarregar**
   - Adiciona os ficheiros à lista de transferência e inicia o download. Os itens ficam disponíveis **24 horas**; depois disso tens de repetir.

5. **Guardar e configurar no projeto**
   - Descompacta os GeoTIFFs para uma pasta (ex.: `C:/dados/dgt/`). Podes ter vários .tif (uma folha por ficheiro).
   - No `.env` indica **a pasta** (ou um único ficheiro):
   ```env
   LIDAR_DGT_PATH=C:/dados/dgt
   ```
   - A API descobre os .tif dentro da pasta (incluindo subpastas) e usa automaticamente a folha que contém o ponto (lat, lon).

**Alternativa:** Catálogo [SNIG](https://snig.dgterritorio.gov.pt/rndg/srv/search) — pesquisa por “DSM” ou “LIDAR”, filtra por formato GeoTIFF e segue os links para descarga. [Dados abertos DGT](https://www.dgterritorio.gov.pt/dados-abertos) também referencia os conjuntos.

---

### Como obter PNOA LIDAR (Espanha)

1. **Entrar no Centro de Descargas**
   - Abre o [Centro de Descargas do CNIG (IGN)](https://centrodedescargas.cnig.es/CentroDescargas/locale?request_locale=en).

2. **Escolher o produto DSM**
   - **Modelo Digital de Superfícies (MDS):** por exemplo **MDS05** (5 m) — [página direta MDS05](https://centrodedescargas.cnig.es/CentroDescargas/modelo-digital-superficies-mds05-primera-cobertura).
   - Ou **MDT** (terreno) se precisares só de elevação do terreno; para telhados interessa o **MDS** (superfície, inclui edifícios).

3. **Selecionar a zona**
   - Escolhe por comunidade autónoma, província, município ou por folhas do MTN25/MTN50 (consoante o produto). O MDS05 distribui por folhas MTN50.

4. **Descarregar**
   - Os ficheiros vêm em formato **COG (Cloud Optimized GeoTIFF)**. Descarrega e descompacta para uma pasta (ex.: `C:/dados/pnoa/`).

5. **Configurar no projeto**
   - Coloca os GeoTIFF/COG numa pasta (ex.: `C:/dados/pnoa/`) e no `.env` indica **a pasta** (ou um único ficheiro):
   ```env
   LIDAR_PNOA_PATH=C:/dados/pnoa
   ```
   - A API escolhe automaticamente a folha que contém o ponto. O Rasterio abre COG sem problema.

**Referência:** [datos.gob.es – Modelo Digital de Superficies](https://datos.gob.es/es/catalogo/e00125901-spaignmds) descreve o conjunto e a licença.

---

**Resumo:** Colocas em `LIDAR_DGT_PATH` ou `LIDAR_PNOA_PATH` o **caminho de um ficheiro .tif** ou de uma **pasta** com vários GeoTIFFs. Se for pasta, a API escolhe sozinha a folha que contém o ponto (lat, lon).

---

## 4. Modelo U-Net (SEGMENTATION_MODEL_PATH)

**O que é:** Checkpoint PyTorch (`.pt`) do modelo de segmentação de telhados.

**Onde obter:**

- **Treino próprio:** O projeto inclui script e documentação para treinar com os teus dados. Ver [docs/treino-unet.md](treino-unet.md). Precisas de pares imagem RGB + máscara binária (telhado = branco).
- **Sem ficheiro:** Se o path não existir ou estiver vazio, a API usa **heurística** (threshold + morfologia) em vez do U-Net. Funciona para testes; para produção é melhor treinar e colocar o `.pt` em `./models/unet_roof.pt` (ou o path que definires no `.env`).

---

## Resumo rápido

| Recurso | Onde obter | Variável .env |
|--------|------------|----------------|
| **Base de dados** | PostgreSQL + PostGIS (local, Docker ou cloud) | `DATABASE_URL` (obrigatório) |
| **Imagem de base** | Ortofoto ou satélite (Sentinel, Planet, etc.); URL que devolva PNG da área, ou vazio | `ORTHO_TILE_URL` |
| **DSM Portugal** | [cdd.dgterritorio.gov.pt](https://cdd.dgterritorio.gov.pt) – descarregar DSM GeoTIFF | `LIDAR_DGT_PATH` (caminho do ficheiro) |
| **DSM Espanha** | [centrodedescargas.cnig.es](https://centrodedescargas.cnig.es) – descarregar DSM | `LIDAR_PNOA_PATH` (caminho do ficheiro) |
| **Modelo U-Net** | Treinar com [docs/treino-unet.md](treino-unet.md) ou deixar vazio (usa heurística) | `SEGMENTATION_MODEL_PATH` |

Para o projeto “funcionar” em termos de API e persistência, só é estritamente necessário ter **PostgreSQL + PostGIS** configurado no `DATABASE_URL`. O resto melhora a qualidade (ortofoto real, inclinação LIDAR, segmentação com U-Net) mas tem fallbacks.
