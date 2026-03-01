# Melhorar máscaras e delimitação de águas

As máscaras e as divisões entre águas podem ficar irregulares (bordas “sujas”, falhas de cobertura, divisões não alinhadas às cumeeiras) mesmo com dataset grande. O que costuma faltar não é só quantidade de imagens.

## O que está a falhar (resumo)

1. **Bordas da máscara** – Não acompanham o contorno real do telhado (jagged, pequenos saltos, falhas nos cantos).
2. **Cobertura** – Pequenas zonas de telhado sem máscara ou pequenos “buracos” dentro da máscara.
3. **Separação de casas** – Dois telhados juntos podem ser segmentados como um só (o modelo de 500 imagens para separar casas pode não estar a ser usado ou não está a generalizar).
4. **Divisão entre águas** – A linha que separa as águas (vermelho/verde) não segue de forma limpa a cumeeira/aresta; fica irregular.

---

## O que está a faltar (por área)

### 1. Dataset e anotação

- **Qualidade > quantidade.** 2000 imagens com bordas e águas mal desenhadas pioram o resultado.
- **Bordas “certinhas” nas máscaras de treino** – Se as máscaras de treino forem pixeladas ou grosseiras, o modelo aprende bordas más.
- **Consistência das águas** – As divisões entre águas nas máscaras multiclasse devem seguir sempre cumeeiras/arestas reais; um critério claro (e documentado) evita confusão.
- **Casos difíceis no dataset** – Incluir muitos exemplos de “duas casas juntas” e de telhados com várias águas e cumeeiras bem definidas.

### 2. Treino do modelo

- **Loss nas bordas** – Usar loss que dá mais peso aos pixels de fronteira (boundary-weighted loss) ou um head auxiliar de bordas.
- **Resolução** – Treinar (ou fine-tune) com resolução maior ou multi-escala para bordas mais finas.
- **Épocas e augmentação** – Garantir treino até convergir e augmentação que preserve bordas (rotação, flip; cuidado com blur excessivo).
- **Modelo “separar casas”** – O modelo treinado com 500 imagens para separar telhados deve ser usado no pipeline (pré-treino binário + ensemble com multiclasse). Verificar se está ativo e se o threshold/ensemble está bem afinado.

### 3. Pós-processamento (código)

- **Limpeza morfológica** – Já existe (`_morphological_cleanup`); pode-se tornar os kernels configuráveis ou um pouco mais agressivos para suavizar bordas, sem apagar detalhe importante.
- **Refinamento de contorno** – Opcional: após obter a máscara, usar deteção de bordas na imagem (Canny, etc.) e “colar” o contorno da máscara às bordas fortes próximas (snapping), para deixar a máscara mais “certinha” no bordo do telhado.
- **Divisão entre águas** – O split por aspect/linhas depende do DSM e do modelo de linhas. Se o DSM for fraco ou a resolução baixa, as divisões ficam irregulares; melhorar DSM ou usar mais o modelo de linhas (cumeeiras) pode ajudar.

### 4. Pipeline

- **Confirmação** – Garantir que o modelo de pré-treino (separar telhados) e o de linhas estão carregados e a ser usados (logs, `.env`, paths no Docker).
- **Threshold** – `SEGMENTATION_PROB_THRESHOLD` e a lógica de ensemble (intersecção pretrain ∩ multiclasse) afetam bordas; valores mal afinados podem “cortar” ou “alargar” a máscara.

---

## Ações concretas (por prioridade)

1. **Rever anotações** – Amostrar 50–100 máscaras do dataset e ver se as bordas e as divisões de águas estão desenhadas de forma limpa e consistente.
2. **Treino com foco em bordas** – Introduzir boundary-weighted loss ou head de bordas e treinar (ou fine-tune) com isso.
3. **Incluir mais “casas juntas”** – Aumentar exemplos de telhados adjacentes e treinar/avaliar explicitamente a separação.
4. **Pós-processamento** – Tornar a limpeza morfológica configurável e, se fizer sentido, adicionar refinamento de contorno por snapping a bordas da imagem.
5. **Verificar pipeline** – Confirmar que os três modelos (pretrain, multiclasse, linhas) estão ativos e que os parâmetros (threshold, ensemble) estão afinados para o teu caso.

---

## Referência no código

- Máscara e limpeza: `src/roof_api/segmentation/mask.py` (`_morphological_cleanup`, `segment_roof_mask`).
- Águas e divisão: `src/roof_api/aguas/waters.py` (`compute_waters`, split por aspect e por linhas).
- Ensemble e modelos: `mask.py` (pretrain + multiclasse), `orchestrator.py` (linhas → `compute_waters`).
