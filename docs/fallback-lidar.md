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
