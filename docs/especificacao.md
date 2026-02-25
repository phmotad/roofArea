# Especificação do Produto — Roof API

## Objetivo

A partir de coordenadas (lat, lon) de um ponto sobre um telhado:

- Identificar automaticamente o telhado
- Gerar máscara visual
- Calcular área total real (3D)
- Identificar, separar e medir as águas do telhado
- Usar inclinação real com dados LIDAR
- Persistir em PostgreSQL/PostGIS
- Retornar JSON estruturado e imagem via API

## Contrato da API

- **Input:** `POST /telhado/analisar` com body `{"lat": <float>, "lon": <float>}`.
- **Output:** JSON com id, área total, lista de águas (área real, inclinação, azimute, WKT), imagem_url, processado_em, fonte_lidar.
- **Erros:** 400 (coordenadas inválidas), 404 (sem dados), 422 (falha processamento), 503 (indisponível).

Ver [api-exemplo.md](api-exemplo.md) para request/response completos.

## Regras de negócio

- Buffer geográfico ~30–40 m; segmentação só classe telhado; águas por slope/aspect (sem ML); área 3D = área_plana / cos(inclinação); fallback sem LIDAR documentado em [fallback-lidar.md](fallback-lidar.md).

## Critérios de sucesso

Medidas coerentes e reproduzíveis; águas identificadas e vetorizadas; imagem legível; suporte Portugal e Espanha; design extensível (solar, seguros, cadastro).
