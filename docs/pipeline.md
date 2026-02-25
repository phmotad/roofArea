# Pipeline de Processamento

## Fluxo principal (pseudocódigo)

```
1. Validar (lat, lon)
2. Verificar cache por (lat, lon); se hit, devolver resultado em cache
3. bounds = bounds_from_point(lat, lon)  # buffer ~35 m
4. rgb, bounds = fetch_ortho(lat, lon)
5. mask = segment_roof_mask(rgb)          # U-Net + morfologia
6. dsm, _, fonte = get_dsm_for_bounds(bounds)
7. waters = compute_waters(mask, dsm, bounds)  # slope/aspect, polígonos, área 3D
8. area_total_m2 = sum(w.area_real_m2 for w in waters)
9. png_bytes = render_roof_image(rgb, mask, waters, bounds)
10. Persistir Telhado + AguaTelhado em PostGIS
11. Guardar PNG em image_store; opcionalmente cache do resultado
12. Devolver AnaliseTelhadoResult (id, área, águas, imagem_url, etc.)
```

## Regras de negócio

- **Buffer:** 30–40 m em torno do ponto (configurável).
- **Área 3D:** `area_real = area_plana / cos(inclinacao_rad)` por água e total.
- **Águas:** Definidas por plano inclinado (slope + aspect); sem ML para separação.
- **Fallback LIDAR:** Se DSM indisponível, slope/aspect a zero; área 3D = área plana; `fonte_lidar = null`.
