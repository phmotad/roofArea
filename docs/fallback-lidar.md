# Estratégia de Fallback sem LIDAR

## Quando não há DSM

- **Condição:** Nenhuma fonte LIDAR (DGT, PNOA) configurada ou dados indisponíveis para o bounding box.
- **Comportamento:** `get_dsm_for_bounds` devolve `(None, None, None)`.

## Impacto no pipeline

1. **Slope e aspect:** Preenchidos com zero em todos os pixels do telhado.
2. **Águas:** Continua a haver pelo menos uma “água” (telhado inteiro) com inclinação 0° e orientação 0°.
3. **Área 3D:** Como `cos(0)=1`, `area_real_m2 = area_plana_m2`; a área total continua a ser a soma das águas.
4. **Resposta API:** `fonte_lidar` fica `null`, indicando que as inclinações não são baseadas em LIDAR.

## Utilização

- Permite usar a API em regiões sem cobertura LIDAR.
- A máscara do telhado e a área plana continuam válidas; apenas inclinação e orientação deixam de ser baseadas em elevação real.

## Saber que lat/lon o LIDAR cobre

Para saber em que coordenadas há DSM disponível:

- **Script:** `python -m scripts.list_lidar_coverage` — lista os bounds (minx, miny, maxx, maxy) de cada tile. Opções: `--geojson` (GeoJSON), `--check LAT LON` (verifica se o ponto está coberto).
- **API:** `GET /lidar/coverage` — devolve a mesma lista em JSON. `GET /lidar/covers?lat=38.82&lon=-9.16` — devolve `{ "covers": true/false, "source": "DGT"|"PNOA", "path": "..." }` quando coberto.
- **Código:** `from roof_api.lidar import get_lidar_coverage, lidar_covers_point` — `get_lidar_coverage()` retorna lista de dicts; `lidar_covers_point(lat, lon)` retorna `True`/`False`.
