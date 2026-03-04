"""
Convert Label Studio polygon export to roof dataset (images/ + masks/) for training.

Label Studio export: JSON with tasks; each task has data.image and annotations[].result
with polygon regions (value.points in percent 0-100, value.polygonlabels).
All polygon labels are merged into one binary mask (telhado=255, resto=0) by default.
Use --labels to restrict which labels count as roof (e.g. aguas,lajes,calaboia).

Usage:
  python -m scripts.label_studio_to_chips --export export.json --images_dir ./my_images --output_dir ./chips
  python -m scripts.label_studio_to_chips --export export.json --images_dir ./imgs --output_dir ./chips --labels "aguas,lajes,a,b,e,calaboia"
  python -m scripts.label_studio_to_chips --export export.json --images_dir ./dados --output_dir ./chips_multiclass --multiclass
  Treino: use o notebook notebooks/kaggle_train_roof_deeplabv3.ipynb (DeepLabV3+ com chips_multiclass).
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

import numpy as np
import cv2
from PIL import Image

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _normalize_label(s: str) -> str:
    return s.strip().lower().replace(" ", "_")


def _image_path_from_task(task: dict, images_dir: Path) -> Path | None:
    data = task.get("data") or {}
    img_ref = data.get("image") or data.get("Image") or ""
    file_upload = task.get("file_upload") or ""
    candidates = []
    if img_ref and not img_ref.startswith("data:"):
        name = Path(img_ref).name
        if "?" in name:
            name = name.split("?")[0]
        candidates.append(name)
    if file_upload:
        candidates.append(Path(file_upload).name if isinstance(file_upload, str) else str(file_upload))
    for name in candidates:
        path = images_dir / name
        if path.exists():
            return path
        for ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
            p = images_dir / (Path(name).stem + ext)
            if p.exists():
                return p
        stem = Path(name).stem
        if "-" in stem:
            short = stem.split("-", 1)[-1]
            for ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
                p = images_dir / (short + ext)
                if p.exists():
                    return p
    for ext in (".png", ".jpg", ".jpeg"):
        all_imgs = sorted(images_dir.glob("*" + ext))
        if all_imgs and "inner_id" in task:
            idx = task.get("inner_id", task.get("id", 0)) - 1
            if 0 <= idx < len(all_imgs):
                return all_imgs[idx]
    return None


CLASS_AGUA = 1
CLASS_CLARABOIA = 2
CLASS_DIVISORIA = 3
CLASS_LAJE = 4
MULTICLASS_LABEL_MAP = {
    "agua_a": CLASS_AGUA,
    "agua_b": CLASS_AGUA,
    "agua_c": CLASS_AGUA,
    "claraboia": CLASS_CLARABOIA,
    "divisoria": CLASS_DIVISORIA,
    "laje": CLASS_LAJE,
}


def _polygons_from_annotation(annotation: dict, include_labels: set[str] | None) -> list[tuple[int, int, list[tuple[float, float]]]]:
    out = []
    for item in annotation.get("result", []):
        if item.get("type") not in ("polygon", "polygonlabels", "polygonlabel"):
            continue
        value = item.get("value") or {}
        points = value.get("points")
        if not points or len(points) < 3:
            continue
        labels = value.get("polygonlabels") or value.get("polygonlabel") or []
        if isinstance(labels, str):
            labels = [labels]
        if include_labels is not None:
            labels_norm = {_normalize_label(l) for l in labels}
            if not labels_norm & include_labels:
                continue
        w = item.get("original_width")
        h = item.get("original_height")
        if w is None or h is None:
            continue
        pts_px = [(float(x) / 100.0 * w, float(y) / 100.0 * h) for x, y in points]
        out.append((int(w), int(h), pts_px))
    return out


def _polygons_with_labels_from_annotation(annotation: dict) -> list[tuple[int, int, list[tuple[float, float]], int]]:
    out = []
    for item in annotation.get("result", []):
        if item.get("type") not in ("polygon", "polygonlabels", "polygonlabel"):
            continue
        value = item.get("value") or {}
        points = value.get("points")
        if not points or len(points) < 3:
            continue
        labels = value.get("polygonlabels") or value.get("polygonlabel") or []
        if isinstance(labels, str):
            labels = [labels]
        label_norm = _normalize_label(labels[0]) if labels else ""
        class_id = MULTICLASS_LABEL_MAP.get(label_norm, 0)
        if class_id == 0:
            continue
        w = item.get("original_width")
        h = item.get("original_height")
        if w is None or h is None:
            continue
        pts_px = [(float(x) / 100.0 * w, float(y) / 100.0 * h) for x, y in points]
        out.append((int(w), int(h), pts_px, class_id))
    return out


def _rasterize_multiclass(
    polygons_with_class: list[tuple[int, int, list[tuple[float, float]], int]],
    width: int,
    height: int,
) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    for _w, _h, pts, class_id in polygons_with_class:
        arr = np.array(pts, dtype=np.float32)
        if arr.size == 0:
            continue
        if _w != width or _h != height:
            scale_x = width / max(_w, 1)
            scale_y = height / max(_h, 1)
            arr[:, 0] *= scale_x
            arr[:, 1] *= scale_y
        pts_int = np.round(arr).astype(np.int32)
        cv2.fillPoly(mask, [pts_int], class_id)
    return mask


def _rasterize_polygons(polygons: list[tuple[int, int, list[tuple[float, float]]]], width: int, height: int) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)
    for _w, _h, pts in polygons:
        arr = np.array(pts, dtype=np.float32)
        if arr.size == 0:
            continue
        if _w != width or _h != height:
            scale_x = width / max(_w, 1)
            scale_y = height / max(_h, 1)
            arr[:, 0] *= scale_x
            arr[:, 1] *= scale_y
        pts_int = np.round(arr).astype(np.int32)
        cv2.fillPoly(mask, [pts_int], 255)
    return mask


def run(export_path: Path, images_dir: Path, output_dir: Path, labels_filter: list[str] | None, multiclass: bool = False) -> int:
    export_path = Path(export_path)
    images_dir = Path(images_dir)
    output_dir = Path(output_dir)
    images_out = output_dir / "images"
    masks_out = output_dir / "masks"
    images_out.mkdir(parents=True, exist_ok=True)
    masks_out.mkdir(parents=True, exist_ok=True)

    raw = json.loads(export_path.read_text(encoding="utf-8"))
    tasks = raw if isinstance(raw, list) else [raw]
    include_labels = None
    if not multiclass and labels_filter:
        include_labels = {_normalize_label(l) for l in labels_filter}
        logger.info("Including only labels: %s", include_labels)
    if multiclass:
        logger.info("Multiclass: 0=fund, 1=agua, 2=claraboia, 3=divisoria, 4=laje")

    count = 0
    for i, task in enumerate(tasks):
        img_path = _image_path_from_task(task, images_dir)
        if not img_path:
            logger.warning("Task %d: no image found in %s", i, images_dir)
            continue
        annotations = task.get("annotations") or []
        if not annotations:
            logger.warning("Task %d (%s): no annotations", i, img_path.name)
            continue
        img = np.array(Image.open(img_path).convert("RGB"), dtype=np.uint8)
        h, w = img.shape[:2]
        if multiclass:
            all_polygons_with_class = []
            for ann in annotations:
                all_polygons_with_class.extend(_polygons_with_labels_from_annotation(ann))
            if not all_polygons_with_class:
                logger.warning("Task %d (%s): no polygon regions with known labels", i, img_path.name)
                continue
            all_polygons_with_class.sort(key=lambda x: -x[3])
            mask = _rasterize_multiclass(all_polygons_with_class, w, h)
        else:
            all_polygons = []
            for ann in annotations:
                all_polygons.extend(_polygons_from_annotation(ann, include_labels))
            if not all_polygons:
                logger.warning("Task %d (%s): no polygon regions (or none matching labels)", i, img_path.name)
                continue
            mask = _rasterize_polygons(all_polygons, w, h)

        stem = img_path.stem
        safe = re.sub(r"[^\w\-]", "_", stem)[:80]
        base = f"{safe}_{i}" if str((task.get("data") or {}).get("image", "")).startswith("http") else safe
        im_out = images_out / f"{base}{img_path.suffix}"
        mask_out = masks_out / f"{base}.png"
        if im_out.suffix.lower() not in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            im_out = images_out / f"{base}.png"
        Image.fromarray(img).save(im_out)
        if multiclass:
            mask_vis = (mask.astype(np.uint8) * 51).astype(np.uint8)
            Image.fromarray(mask_vis).save(mask_out)
        else:
            Image.fromarray(mask).save(mask_out)
        count += 1
        logger.info("Written %s + %s", im_out.name, mask_out.name)

    return count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert Label Studio polygon export to images/ + masks/ for U-Net training.",
    )
    parser.add_argument(
        "--export",
        type=str,
        required=True,
        help="Path to Label Studio JSON export (Export -> JSON in the UI).",
    )
    parser.add_argument(
        "--images_dir",
        type=str,
        required=True,
        help="Folder where the original images are (same filenames as in the export).",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./chips",
        help="Output root for images/ and masks/ (default: ./chips).",
    )
    parser.add_argument(
        "--labels",
        type=str,
        default=None,
        help="Comma-separated list of polygon labels to include as roof (default: all). E.g. aguas,lajes,calaboia,a,b,e,divisoria.",
    )
    parser.add_argument(
        "--multiclass",
        action="store_true",
        help="Output multiclass masks: 0=fundo, 1=agua, 2=claraboia, 3=divisoria, 4=laje. Use for U-Net --num_classes 5.",
    )
    args = parser.parse_args()
    labels_list = [s.strip() for s in args.labels.split(",")] if args.labels else None
    n = run(
        Path(args.export),
        Path(args.images_dir),
        Path(args.output_dir),
        labels_list,
        multiclass=args.multiclass,
    )
    if n == 0:
        logger.error("No tasks converted. Check --export, --images_dir and that annotations use polygon/polygonlabels.")
        sys.exit(1)
    logger.info("Done. %d image/mask pairs in %s. Train with notebook kaggle_train_roof_deeplabv3.ipynb", n, args.output_dir)


if __name__ == "__main__":
    main()
