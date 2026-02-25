# Performance e Escalabilidade

## Cache

- **Chave:** Hash de (lat, lon) com precisão fixa (ex.: 6 casas decimais).
- **TTL:** Configurável (`CACHE_TTL_SECONDS`); 0 desativa o cache.
- **Implementação atual:** In-memory; para produção considerar Redis ou similar.

## Base de dados

- **Índices:** (lat, lon) em `telhados`; `telhado_id` em `aguas_telhado`.
- **PostGIS:** Índices espaciais (GIST) em colunas de geometria se houver consultas por extensão.
- **Conexões:** Usar pool assíncrono (asyncpg); limitar o tamanho do pool conforme carga.

## Workers e filas

- **MVP:** Um processo uvicorn; várias workers com `--workers N` para mais concorrência.
- **Futuro:** Colocar o pipeline pesado (ortofoto + segmentação + DSM) numa fila (Celery, RQ, etc.) e devolver resultado por polling ou WebSocket.

## Orquestração

- Falhas numa etapa (ex.: LIDAR) não travam o fluxo; fallback documentado em [fallback-lidar.md](fallback-lidar.md).
- Tempos típicos: ortofoto e DSM dependem de rede/IO; U-Net de GPU/CPU; o resto é rápido.
