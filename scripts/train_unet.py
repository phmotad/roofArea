"""
Train U-Net for roof segmentation. Saves checkpoint compatible with load_unet().

Usage:
  python -m scripts.train_unet --data_dir ./data/roof --output ./models/unet_roof.pt
  python -m scripts.train_unet --data_dir ./data/roof --images images --masks masks --epochs 50
  # Multiclass + same resolution as API (512x512):
  python -m scripts.train_unet --data_dir ./chips_multiclass --output ./models/unet_roof_multiclass.pt --num_classes 5 --size 512 512 --epochs 50
  # AMD GPU via DirectML (pip install torch-directml):
  python -m scripts.train_unet --data_dir ./chips_multiclass --output ./models/unet_roof_multiclass.pt --num_classes 5 --device dml
  # Dice loss (melhor com classes desequilibradas, ver dida blog):
  python -m scripts.train_unet --data_dir ./chips_multiclass --output ./models/unet_roof_multiclass.pt --num_classes 5 --loss dice
"""

import argparse
import logging
import sys
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

# Ensure project root and src are on path when run as script
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "src"))

from roof_api.segmentation.dataset import RoofDataset
from roof_api.segmentation.unet_model import UNet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True,
)
logger = logging.getLogger(__name__)
for h in logging.root.handlers:
    if hasattr(h, "stream"):
        try:
            h.stream.reconfigure(line_buffering=True)
        except Exception:
            pass


def dice_coef(y_pred: torch.Tensor, y_true: torch.Tensor, smooth: float = 1e-6) -> torch.Tensor:
    """Batch Dice coefficient (0-1, higher is better). Binary: y_true (1,H,W), logits (B,1,H,W)."""
    pred = (torch.sigmoid(y_pred) > 0.5).float()
    intersection = (pred * y_true).sum(dim=(2, 3))
    union = pred.sum(dim=(2, 3)) + y_true.sum(dim=(2, 3))
    return (2 * intersection + smooth) / (union + smooth)


class BinaryDiceLoss(nn.Module):
    """Dice loss para segmentação binária (diferenciável, usa sigmoid). 1 - Dice."""

    def __init__(self, smooth: float = 1e-6):
        super().__init__()
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        pred = torch.sigmoid(logits)
        intersection = (pred * y).sum(dim=(2, 3))
        union = pred.sum(dim=(2, 3)) + y.sum(dim=(2, 3))
        dice = (2 * intersection + self.smooth) / (union + self.smooth)
        return 1 - dice.mean()


class MulticlassDiceLoss(nn.Module):
    """Dice loss por classe (média sobre classes). Melhor com desequilíbrio (dida blog)."""

    def __init__(self, num_classes: int, smooth: float = 1e-6):
        super().__init__()
        self.num_classes = num_classes
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
        pred = torch.softmax(logits, dim=1)
        loss = 0.0
        for k in range(self.num_classes):
            y_k = (y == k).float()
            pred_k = pred[:, k]
            inter = (pred_k * y_k).sum(dim=(1, 2))
            union = pred_k.sum(dim=(1, 2)) + y_k.sum(dim=(1, 2))
            dice = (2 * inter + self.smooth) / (union + self.smooth)
            loss = loss + (1 - dice.mean())
        return loss / max(self.num_classes, 1)


def multiclass_accuracy(logits: torch.Tensor, y: torch.Tensor) -> float:
    """Per-pixel accuracy for (B, C, H, W) logits and (B, H, W) long labels."""
    pred = logits.argmax(dim=1)
    return (pred == y).float().mean().item()


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    criterion: nn.Module,
    num_classes: int = 1,
    epoch: int = 0,
) -> tuple[float, float]:
    model.train()
    total_loss = 0.0
    total_metric = 0.0
    n = 0
    total_batches = len(loader)
    for batch_idx, (x, y) in enumerate(loader):
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        with torch.no_grad():
            if num_classes > 1:
                total_metric += multiclass_accuracy(logits, y)
            else:
                total_metric += dice_coef(logits, y).mean().item()
        n += 1
        if total_batches >= 10 and (batch_idx + 1) % max(1, total_batches // 5) == 0:
            logger.info("  Epoch %d: batch %d/%d", epoch, batch_idx + 1, total_batches)
            sys.stderr.flush()
    return total_loss / max(n, 1), total_metric / max(n, 1)


@torch.no_grad()
def validate(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
    criterion: nn.Module,
    num_classes: int = 1,
) -> tuple[float, float]:
    model.eval()
    total_loss = 0.0
    total_metric = 0.0
    n = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        logits = model(x)
        total_loss += criterion(logits, y).item()
        if num_classes > 1:
            total_metric += multiclass_accuracy(logits, y)
        else:
            total_metric += dice_coef(logits, y).mean().item()
        n += 1
    return total_loss / max(n, 1), total_metric / max(n, 1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train U-Net for roof segmentation (telhado class)."
    )
    parser.add_argument(
        "--data_dir",
        type=str,
        required=True,
        help="Root directory containing images/ and masks/ subdirs (or use --images/--masks).",
    )
    parser.add_argument(
        "--images",
        type=str,
        default="images",
        help="Subdir name for RGB images (default: images).",
    )
    parser.add_argument(
        "--masks",
        type=str,
        default="masks",
        help="Subdir name for binary masks 0/255 (default: masks).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./models/unet_roof.pt",
        help="Path to save best checkpoint (default: ./models/unet_roof.pt).",
    )
    parser.add_argument(
        "--size",
        type=int,
        nargs=2,
        default=[256, 256],
        metavar=("H", "W"),
        help="Training patch size (default: 256 256).",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Number of epochs (default: 50).",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=8,
        help="Batch size (default: 8).",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=1e-3,
        help="Learning rate (default: 1e-3).",
    )
    parser.add_argument(
        "--val_ratio",
        type=float,
        default=0.2,
        help="Fraction of data for validation (default: 0.2).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="DataLoader workers (default: 0).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42).",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        choices=("cuda", "cpu", "dml"),
        help="Device: cuda (NVIDIA), dml (AMD/Intel via DirectML), cpu.",
    )
    parser.add_argument(
        "--num_classes",
        type=int,
        default=1,
        help="Number of classes (1=binary roof mask; 5=multiclass: fund, agua, claraboia, divisoria, laje). Default: 1.",
    )
    parser.add_argument(
        "--pretrain",
        type=str,
        default=None,
        help="Path to pretrained checkpoint (binary) to load encoder/decoder; output layer initialized randomly for num_classes.",
    )
    parser.add_argument(
        "--loss",
        type=str,
        default="auto",
        choices=("auto", "bce", "dice", "ce"),
        help="Loss: auto (bce/dice binário, ce multiclasse), bce/dice (binário), ce/dice (multiclasse). Dice ajuda com desequilíbrio (dida).",
    )
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    if args.device == "cuda":
        if not torch.cuda.is_available():
            logger.error("CUDA requested but not available. Install PyTorch with CUDA: pip install torch --index-url https://download.pytorch.org/whl/cu121")
            sys.exit(1)
        device = torch.device("cuda")
    elif args.device == "dml":
        try:
            import torch_directml
            device = torch_directml.device()
            logger.info("Using DirectML (AMD/Intel GPU)")
        except ImportError:
            logger.error("DirectML requested but torch-directml not installed. Run: pip install torch-directml")
            sys.exit(1)
    else:
        device = torch.device("cpu")
    logger.info("Device: %s", device)

    data_dir = Path(args.data_dir)
    images_dir = data_dir / args.images
    masks_dir = data_dir / args.masks
    if not images_dir.is_dir() or not masks_dir.is_dir():
        logger.error("Directories not found: %s, %s", images_dir, masks_dir)
        sys.exit(1)

    num_classes = max(1, int(args.num_classes))
    full = RoofDataset(
        images_dir,
        masks_dir,
        size=tuple(args.size),
        augment=True,
        num_classes=num_classes,
    )
    n = len(full)
    if n == 0:
        logger.error("No image/mask pairs found. Check --data_dir and subdirs.")
        sys.exit(1)
    n_val = max(1, int(n * args.val_ratio))
    n_train = n - n_val
    logger.info("Dataset: %d train, %d val", n_train, n_val)
    sys.stdout.flush()
    sys.stderr.flush()
    train_ds, val_ds = random_split(full, [n_train, n_val], generator=torch.Generator().manual_seed(args.seed))
    pin_memory = args.device == "cuda"
    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
        pin_memory=pin_memory,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
    )

    model = UNet(in_channels=3, out_channels=num_classes).to(device)
    if args.pretrain:
        pretrain_path = Path(args.pretrain)
        if pretrain_path.exists():
            state = torch.load(pretrain_path, map_location=device, weights_only=True)
            sd = state.get("model", state) if isinstance(state, dict) else state
            model_sd = model.state_dict()
            filtered = {k: v for k, v in sd.items() if k in model_sd and v.shape == model_sd[k].shape}
            model.load_state_dict(filtered, strict=False)
            logger.info("Loaded pretrained weights from %s (%d/%d params)", pretrain_path, len(filtered), len(sd))
        else:
            logger.warning("Pretrain path not found: %s", pretrain_path)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    if num_classes == 1:
        criterion = BinaryDiceLoss() if args.loss == "dice" else nn.BCEWithLogitsLoss()
        metric_name = "dice"
    else:
        criterion = MulticlassDiceLoss(num_classes) if args.loss == "dice" else nn.CrossEntropyLoss()
        metric_name = "acc"
    loss_name = "Dice" if args.loss == "dice" else ("BCE" if num_classes == 1 else "CrossEntropy")
    logger.info("Loss: %s", loss_name)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    best_val_loss = float("inf")

    logger.info("Iniciando treino: %d epocas", args.epochs)
    sys.stdout.flush()
    sys.stderr.flush()
    for epoch in range(1, args.epochs + 1):
        train_loss, train_metric = train_one_epoch(
            model, train_loader, optimizer, device, criterion, num_classes=num_classes, epoch=epoch
        )
        val_loss, val_metric = validate(model, val_loader, device, criterion, num_classes=num_classes)
        logger.info(
            "Epoch %d | train loss=%.4f %s=%.4f | val loss=%.4f %s=%.4f",
            epoch,
            train_loss,
            metric_name,
            train_metric,
            val_loss,
            metric_name,
            val_metric,
        )
        sys.stderr.flush()
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            state = {
                "model": model.state_dict(),
                "epoch": epoch,
                "best_val_loss": best_val_loss,
                "val_metric": val_metric,
                "num_classes": num_classes,
            }
            torch.save(state, output_path)
            logger.info("Saved best checkpoint to %s", output_path)

    logger.info("Training finished. Best model: %s", output_path)


if __name__ == "__main__":
    main()
