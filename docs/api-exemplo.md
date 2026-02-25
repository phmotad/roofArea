# Exemplo de Request/Response da API

## Request

**POST** `/telhado/analisar`

```json
{
  "lat": 38.72,
  "lon": -9.14
}
```

## Response (201 Created)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "lat": 38.72,
  "lon": -9.14,
  "area_total_m2": 125.4,
  "aguas": [
    {
      "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "area_real_m2": 62.1,
      "inclinacao_graus": 28.5,
      "orientacao_azimute": 180,
      "geometria_wkt": "POLYGON((...))"
    }
  ],
  "imagem_url": "/telhados/550e8400-e29b-41d4-a716-446655440000/imagem.png",
  "imagem_base64": null,
  "processado_em": "2025-02-05T12:00:00Z",
  "fonte_lidar": "DGT"
}
```

## Obter a imagem

**GET** `/telhados/{id}/imagem.png` — devolve PNG (Content-Type: image/png).

## Erros

- **400** — Coordenadas inválidas (lat/lon fora dos intervalos).
- **404** — Sem dados para a região (ex.: ortofoto indisponível).
- **422** — Falha de processamento (ex.: segmentação falhou).
- **503** — Serviço temporariamente indisponível.
