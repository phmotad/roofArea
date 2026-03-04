"""
Gera máscaras multiclasse a partir dos NPZ em roof/chips_segmentos/gt/ para
fine-tuning: 0 = fundo (nada), 1 = linha divisória, 2 = água (cada plano do telhado; telhado = conjunto das águas).

Os NPZ contêm apenas segmentos de linha (chave 'lines', forma Nx2x2). O resto
do chip pode ser interpretado de duas formas:
- modo "fill": preencher telhados (regiões fechadas) a partir das linhas (recomendado).
- modo "all": assumir que todo o chip é telhado (legado).

Uso:
  python -m scripts.generate_finetuning_masks_from_segmentos --segmentos_dir roof/chips_segmentos
  python -m scripts.generate_finetuning_masks_from_segmentos --segmentos_dir roof/chips_segmentos --out_masks masks_3class --border 8
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

_root = Path(__file__).resolve().parent.parent

CLASS_FUNDO = 0
CLASS_LINHA = 1
CLASS_AGUA = 2  # cada plano do telhado; telhado = conjunto das águas dentro das bordas
NUM_CLASSES = 3


def load_wireframe(npz_path: Path) -> np.ndarray:
    """Segmentos de linha do NPZ (chave 'lines'), forma (N, 2, 2)."""
    data = np.load(npz_path, allow_pickle=True)
    return np.asarray(data["lines"], dtype=np.float64)


def rasterize_lines(lines: np.ndarray, shape_hw: tuple[int, int], thickness: int = 2) -> np.ndarray:
    """Desenha linhas com valor CLASS_LINHA (1); resto 0."""
    h, w = shape_hw
    out = np.zeros((h, w), dtype=np.uint8)
    for i in range(len(lines)):
        seg = lines[i]
        pt1 = (int(round(seg[0, 0])), int(round(seg[0, 1])))
        pt2 = (int(round(seg[1, 0])), int(round(seg[1, 1])))
        cv2.line(out, pt1, pt2, CLASS_LINHA, thickness)
    return out


def build_three_class_mask(
    lines: np.ndarray,
    shape_hw: tuple[int, int],
    line_thickness: int = 2,
    border_px: int = 5,
    fill_roofs: bool = True,
    close_kernel: int = 3,
    close_iters: int = 2,
    dilate_kernel: int = 3,
    dilate_iters: int = 1,
    min_roof_area_px: int = 50,
) -> np.ndarray:
    """
    Máscara (H, W) uint8: 0=fundo, 1=linha divisória, 2=água (cada plano; telhado = conjunto das águas).
    - Linhas do NPZ → 1.
    - Faixa de border_px na borda da imagem → 0 (fundo).
    - Se fill_roofs=True: água = regiões fechadas pelas linhas (preenchidas).
    - Se fill_roofs=False: resto → 2 (água) (legado).
    """
    h, w = shape_hw
    mask = np.full((h, w), CLASS_AGUA, dtype=np.uint8) if not fill_roofs else np.full((h, w), CLASS_FUNDO, dtype=np.uint8)
    if border_px > 0:
        mask[:border_px, :] = CLASS_FUNDO
        mask[-border_px:, :] = CLASS_FUNDO
        mask[:, :border_px] = CLASS_FUNDO
        mask[:, -border_px:] = CLASS_FUNDO
    line_map = rasterize_lines(lines, (h, w), line_thickness)
    if fill_roofs:
        # Preencher telhados a partir das linhas: fechar pequenos gaps e preencher por contornos.
        edges = (line_map > 0).astype(np.uint8) * 255

        if close_kernel >= 3 and close_iters > 0:
            k = int(close_kernel)
            if k % 2 == 0:
                k += 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=int(close_iters))

        if dilate_kernel >= 3 and dilate_iters > 0:
            k = int(dilate_kernel)
            if k % 2 == 0:
                k += 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
            edges = cv2.dilate(edges, kernel, iterations=int(dilate_iters))

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        roofs = np.zeros((h, w), dtype=np.uint8)
        for c in contours:
            area = float(cv2.contourArea(c))
            if area < float(min_roof_area_px):
                continue
            cv2.drawContours(roofs, [c], -1, 255, thickness=-1)

        # Em algumas imagens, as linhas não fecham e o contorno não aparece;
        # nesse caso fazemos fallback para flood-fill do fundo e usamos o restante como "telhado".
        roof_px = int((roofs > 0).sum())
        if roof_px < int(0.005 * h * w):
            free = cv2.bitwise_not(edges)
            ff = free.copy()
            flood_mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
            cv2.floodFill(ff, flood_mask, seedPoint=(0, 0), newVal=0)
            roofs = (ff == 255).astype(np.uint8) * 255

        if border_px > 0:
            roofs[:border_px, :] = 0
            roofs[-border_px:, :] = 0
            roofs[:, :border_px] = 0
            roofs[:, -border_px:] = 0

        mask[roofs > 0] = CLASS_AGUA

    mask[line_map == CLASS_LINHA] = CLASS_LINHA
    return mask


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gerar máscaras 3-class (fundo, linha, água) a partir dos NPZ em chips_segmentos/gt/."
    )
    parser.add_argument(
        "--segmentos_dir",
        type=str,
        default=None,
        help="Pasta chips_segmentos (default: roof/chips_segmentos)",
    )
    parser.add_argument(
        "--out_masks",
        type=str,
        default="masks_3class",
        help="Nome da subpasta onde gravar máscaras (default: masks_3class)",
    )
    parser.add_argument("--line_thickness", type=int, default=2, help="Espessura das linhas em px")
    parser.add_argument(
        "--border",
        type=int,
        default=5,
        help="Largura da faixa de borda em px para a classe fundo (0)",
    )
    parser.add_argument(
        "--fill_roofs",
        action="store_true",
        help="Preencher águas (regiões fechadas) a partir das linhas (recomendado).",
    )
    parser.add_argument(
        "--close_kernel",
        type=int,
        default=3,
        help="Kernel (ímpar) para fechar gaps nas linhas antes de preencher (default: 3).",
    )
    parser.add_argument(
        "--close_iters",
        type=int,
        default=2,
        help="Iterações de fechamento morfológico antes do preenchimento (default: 2).",
    )
    parser.add_argument(
        "--dilate_kernel",
        type=int,
        default=3,
        help="Kernel (ímpar) para dilatar linhas antes de extrair contornos (default: 3).",
    )
    parser.add_argument(
        "--dilate_iters",
        type=int,
        default=1,
        help="Iterações de dilatação antes de extrair contornos (default: 1).",
    )
    parser.add_argument(
        "--min_roof_area_px",
        type=int,
        default=50,
        help="Área mínima (px) de contorno para considerar água (default: 50).",
    )
    parser.add_argument(
        "--use_building_masks",
        type=str,
        default="",
        help="Subpasta com máscaras de telhado já preenchidas (ex.: building_masks_renamed). Se existir {stem}.png, usa como classe telhado e sobrepõe linhas do NPZ.",
    )
    args = parser.parse_args()

    seg_dir = Path(args.segmentos_dir) if args.segmentos_dir else _root / "roof" / "chips_segmentos"
    gt_dir = seg_dir / "gt"
    img_dir = seg_dir / "images"
    out_masks_dir = seg_dir / args.out_masks
    building_masks_dir = seg_dir / args.use_building_masks if args.use_building_masks else None

    if not gt_dir.is_dir() or not img_dir.is_dir():
        print("Precisamos de", gt_dir, "e", img_dir)
        return

    out_masks_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for npz_path in sorted(gt_dir.glob("*.npz")):
        stem = npz_path.stem
        im_path = img_dir / f"{stem}.png"
        if not im_path.exists():
            im_path = img_dir / f"{stem}.jpg"
        if not im_path.exists():
            continue
        img = cv2.imread(str(im_path))
        if img is None:
            continue
        h, w = img.shape[:2]
        lines = load_wireframe(npz_path)
        roof_from_building = None
        if building_masks_dir and building_masks_dir.is_dir():
            bm_path = building_masks_dir / f"{stem}.png"
            if bm_path.exists():
                bm = cv2.imread(str(bm_path), cv2.IMREAD_GRAYSCALE)
                if bm is not None and bm.size > 0:
                    if bm.shape[0] != h or bm.shape[1] != w:
                        bm = cv2.resize(bm, (w, h), interpolation=cv2.INTER_NEAREST)
                    roof_from_building = (bm > 127).astype(np.uint8)

        if roof_from_building is not None:
            mask = np.full((h, w), CLASS_FUNDO, dtype=np.uint8)
            mask[roof_from_building > 0] = CLASS_AGUA
            if args.border > 0:
                mask[: args.border, :] = CLASS_FUNDO
                mask[-args.border :, :] = CLASS_FUNDO
                mask[:, : args.border] = CLASS_FUNDO
                mask[:, -args.border :] = CLASS_FUNDO
            if lines is not None and len(lines) > 0:
                line_map = rasterize_lines(lines, (h, w), args.line_thickness)
                mask[line_map == CLASS_LINHA] = CLASS_LINHA
        elif lines is None or len(lines) == 0:
            mask = np.full((h, w), CLASS_AGUA, dtype=np.uint8)
            if args.border > 0:
                mask[: args.border, :] = CLASS_FUNDO
                mask[-args.border :, :] = CLASS_FUNDO
                mask[:, : args.border] = CLASS_FUNDO
                mask[:, -args.border :] = CLASS_FUNDO
        else:
            mask = build_three_class_mask(
                lines,
                (h, w),
                line_thickness=args.line_thickness,
                border_px=args.border,
                fill_roofs=bool(args.fill_roofs),
                close_kernel=int(args.close_kernel),
                close_iters=int(args.close_iters),
                dilate_kernel=int(args.dilate_kernel),
                dilate_iters=int(args.dilate_iters),
                min_roof_area_px=int(args.min_roof_area_px),
            )
        out_path = out_masks_dir / f"{stem}.png"
        cv2.imwrite(str(out_path), mask)
        n += 1
    print(
        "Máscaras 3-class (0=fundo, 1=linha, 2=água) geradas:",
        n,
        "em",
        out_masks_dir,
    )
    print("Para fine-tuning: use images em", img_dir, "e masks em", out_masks_dir, "com num_classes=3.")


if __name__ == "__main__":
    main()
