# Arquitetura de Produção — Pipeline de Análise de Telhados

Fluxo canónico para produção: da imagem satélite ao PostGIS.

## Diagrama do pipeline

```
Imagem Satélite (ortofoto)
         ↓
    DeepLabV3
         ↓
  Máscara Telhado
         ↓
  Recorte do LIDAR (DSM)
         ↓
  Clustering por inclinação (slope/aspect)
         ↓
  Separação das águas
         ↓
  Cálculo de área por instância
         ↓
  Salvar no PostGIS
```

## Mapeamento para o código

| Etapa | Descrição | Módulo / função |
|-------|-----------|------------------|
| **Imagem Satélite** | Ortofoto RGB para o bounds (lat, lon + buffer). | `geo.acquisition` / `fetch_ortho(lat, lon)` |
| **DeepLabV3** | Segmentação semântica (telhado, águas, divisorias). | `segmentation.mask` / `segment_roof_mask`, `segment_roof_and_waters` |
| **Máscara Telhado** | Máscara binária do telhado (pós-processamento morfológico). | Saída do DeepLabV3 + `_morphological_cleanup` |
| **Recorte do LIDAR** | DSM (Digital Surface Model) para o mesmo bounds. | `lidar.dsm` / `get_dsm_for_bounds(minx, miny, maxx, maxy)` |
| **Clustering por inclinação** | Slope e aspect por pixel a partir do DSM; agrupamento por plano. | `aguas.slope_aspect` / `slope_aspect_from_dsm`; `aguas.waters` / `compute_waters` (regiões + aspect) |
| **Separação das águas** | Divisão de regiões por orientação (aspect) distinta; uma “água” por plano. | `aguas.waters` / `_try_split_region_by_aspect`, `compute_waters` |
| **Cálculo de área por instância** | Área plana (m²) e área real 3D por água: `area_real = area_plana / cos(inclinacao)`. | `aguas.waters` / `WaterPolygon` (area_plana_m2, area_real_m2, inclinacao_graus, orientacao_azimute) |
| **Salvar no PostGIS** | Persistência de telhado (ponto, bounds, área total, fonte_lidar) e águas (geometria, área, inclinação, azimute). | `db.models` (Telhado, AguaTelhado); `services.orchestrator` / `analyse_roof` (commit) |

## Orquestração

O fluxo acima é executado em sequência em `services.orchestrator.analyse_roof(lat, lon)`:

1. Validação (lat, lon) e cache.
2. `fetch_ortho` → imagem satélite.
3. DeepLabV3 → máscara (e opcional máscara de águas).
4. `get_dsm_for_bounds` → recorte LIDAR (DSM).
5. `compute_waters(mask, dsm, bounds, ...)` → clustering por inclinação, separação das águas, cálculo de área por instância.
6. Filtro pelo ponto (lat, lon): telhado que contém o ponto ou mais próximo.
7. Renderização da imagem (opcional).
8. Persistência em PostGIS (Telhado + AguaTelhado) e image store.
9. Devolução do resultado (DTO) e atualização do cache.

## Fallback sem LIDAR

Se não houver DSM para o bounds: o recorte LIDAR devolve `None`. O clustering por inclinação usa slope/aspect zero; todas as águas ficam com inclinação 0° e orientação 0°; área real = área plana; `fonte_lidar = null`. O resto do pipeline mantém-se.

## Documentação relacionada

- [Arquitetura (visão geral)](arquitetura.md)
- [Pipeline (pseudocódigo e regras)](pipeline.md)
- [Fallback sem LIDAR](fallback-lidar.md)
