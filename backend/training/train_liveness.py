"""
train_liveness.py — Full Training Pipeline for Passive Liveness CNN

Architecture: MobileNetV3-Small pretrained on ImageNet,
fine-tuned on CelebA-Spoof + NUAA + CASIA-SURF

Training features:
  - Aggressive augmentation: brightness, blur, JPEG compression, noise
  - Focal Loss (handles class imbalance between live/spoof)
  - Early stopping on validation AUC
  - Mixed precision (AMP) for GPU acceleration
  - Comprehensive logging and checkpointing

Directory structure expected:
  data/liveness/
    train/
      live/   *.jpg
      spoof/  *.jpg
    val/
      live/   *.jpg
      spoof/  *.jpg

Usage:
  python -m training.train_liveness --data_root data/liveness --epochs 30
"""

import argparse
import logging
import os
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
from sklearn.metrics import roc_auc_score, classification_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Focal Loss — handles class imbalance
# ═══════════════════════════════════════════════════════════════════════════

class FocalLoss(nn.Module):
    """
    Focal Loss: down-weights easy examples, focuses learning on hard ones.
    FL(p_t) = -α_t × (1 - p_t)^γ × log(p_t)

    Particularly effective for liveness detection where spoof samples
    may be easier to classify than edge-case live samples.
    """

    def __init__(self, alpha: float = 0.75, gamma: float = 2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce = nn.functional.binary_cross_entropy(inputs, targets, reduction="none")
        p_t = inputs * targets + (1 - inputs) * (1 - targets)
        alpha_t = self.alpha * targets + (1 - self.alpha) * (1 - targets)
        focal_weight = alpha_t * (1 - p_t) ** self.gamma
        return (focal_weight * bce).mean()


# ═══════════════════════════════════════════════════════════════════════════
# Dataset
# ═══════════════════════════════════════════════════════════════════════════

class SpoofAugmentation:
    """
    Custom augmentations that simulate real-world spoofing artifacts:
    random blur, JPEG compression, noise, screen patterns.
    """

    def __call__(self, img):
        # Random JPEG compression (simulates re-encoding artifacts)
        if np.random.random() < 0.3:
            quality = np.random.randint(20, 80)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            _, encoded = cv2.imencode(".jpg", np.array(img), encode_param)
            img = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

        # Random Gaussian blur (simulates camera defocus)
        if np.random.random() < 0.3:
            ksize = np.random.choice([3, 5, 7])
            img = cv2.GaussianBlur(np.array(img), (ksize, ksize), 0)

        # Random brightness/contrast
        if np.random.random() < 0.4:
            alpha = np.random.uniform(0.7, 1.3)  # contrast
            beta = np.random.randint(-30, 30)     # brightness
            img = cv2.convertScaleAbs(np.array(img), alpha=alpha, beta=beta)

        # Gaussian noise (simulates sensor noise variations)
        if np.random.random() < 0.2:
            noise = np.random.normal(0, 10, np.array(img).shape).astype(np.uint8)
            img = cv2.add(np.array(img), noise)

        return img


class LivenessDataset(Dataset):
    """
    Binary liveness dataset.
    Expects: data_root/{train,val}/{live,spoof}/*.jpg
    """

    def __init__(self, root_dir: str, split: str = "train", transform=None):
        self.samples = []
        self.labels = []
        self.transform = transform

        root = Path(root_dir) / split

        live_dir = root / "live"
        spoof_dir = root / "spoof"

        if live_dir.exists():
            for f in live_dir.glob("*.jpg"):
                self.samples.append(str(f))
                self.labels.append(1.0)  # live = 1

        if spoof_dir.exists():
            for f in spoof_dir.glob("*.jpg"):
                self.samples.append(str(f))
                self.labels.append(0.0)  # spoof = 0

        # Also check for .png files
        if live_dir.exists():
            for f in live_dir.glob("*.png"):
                self.samples.append(str(f))
                self.labels.append(1.0)
        if spoof_dir.exists():
            for f in spoof_dir.glob("*.png"):
                self.samples.append(str(f))
                self.labels.append(0.0)

        logger.info(f"[{split}] Loaded {len(self.samples)} samples "
                     f"(live={self.labels.count(1.0)}, spoof={self.labels.count(0.0)})")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img = cv2.imread(self.samples[idx])
        if img is None:
            # Return a blank image if file is corrupted
            img = np.zeros((112, 112, 3), dtype=np.uint8)

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (112, 112))

        if self.transform:
            img = self.transform(img)

        label = torch.tensor(self.labels[idx], dtype=torch.float32)
        return img, label


# ═══════════════════════════════════════════════════════════════════════════
# Training Loop
# ═══════════════════════════════════════════════════════════════════════════

def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Training on: {device}")

    # ─── Transforms ─────────────────────────────────────────────────────
    spoof_aug = SpoofAugmentation()

    train_transform = transforms.Compose([
        transforms.Lambda(lambda x: spoof_aug(x)),
        transforms.ToPILImage(),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.2),
    ])

    val_transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # ─── Data ───────────────────────────────────────────────────────────
    train_dataset = LivenessDataset(args.data_root, "train", train_transform)
    val_dataset = LivenessDataset(args.data_root, "val", val_transform)

    if len(train_dataset) == 0:
        logger.error("No training data found! Check your data directory.")
        logger.info(f"Expected structure: {args.data_root}/train/{{live,spoof}}/*.jpg")
        return

    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size, shuffle=True,
        num_workers=args.workers, pin_memory=True,
    )
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch_size, shuffle=False,
        num_workers=args.workers, pin_memory=True,
    ) if len(val_dataset) > 0 else None

    # ─── Model ──────────────────────────────────────────────────────────
    model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    model.classifier = nn.Sequential(
        nn.Linear(576, 256),
        nn.Hardswish(),
        nn.Dropout(p=0.3),
        nn.Linear(256, 1),
        nn.Sigmoid(),
    )
    model = model.to(device)

    # ─── Loss, Optimizer, Scheduler ─────────────────────────────────────
    criterion = FocalLoss(alpha=0.75, gamma=2.0)
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    # Mixed precision
    scaler = torch.amp.GradScaler(enabled=(device.type == "cuda"))

    # Early stopping
    best_auc = 0.0
    patience_counter = 0
    save_dir = Path(args.save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    # ─── Training ───────────────────────────────────────────────────────
    for epoch in range(args.epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        t0 = time.time()

        for batch_idx, (images, labels) in enumerate(train_loader):
            images = images.to(device)
            labels = labels.to(device)

            with torch.amp.autocast(device_type=device.type, enabled=(device.type == "cuda")):
                outputs = model(images).squeeze(-1)
                loss = criterion(outputs, labels)

            optimizer.zero_grad()
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_loss += loss.item()
            predicted = (outputs > 0.5).float()
            correct += (predicted == labels).sum().item()
            total += labels.size(0)

        scheduler.step()

        train_loss = running_loss / len(train_loader)
        train_acc = correct / total * 100
        elapsed = time.time() - t0

        # ─── Validation ────────────────────────────────────────────────
        val_auc = 0.0
        if val_loader:
            model.eval()
            all_preds = []
            all_labels = []

            with torch.no_grad():
                for images, labels in val_loader:
                    images = images.to(device)
                    outputs = model(images).squeeze(-1)
                    all_preds.extend(outputs.cpu().numpy())
                    all_labels.extend(labels.numpy())

            all_preds = np.array(all_preds)
            all_labels = np.array(all_labels)

            try:
                val_auc = roc_auc_score(all_labels, all_preds)
            except ValueError:
                val_auc = 0.0

            val_acc = np.mean((all_preds > 0.5) == all_labels) * 100

            logger.info(
                f"Epoch [{epoch+1}/{args.epochs}]  "
                f"Loss: {train_loss:.4f}  "
                f"Train Acc: {train_acc:.1f}%  "
                f"Val Acc: {val_acc:.1f}%  "
                f"Val AUC: {val_auc:.4f}  "
                f"Time: {elapsed:.1f}s"
            )
        else:
            logger.info(
                f"Epoch [{epoch+1}/{args.epochs}]  "
                f"Loss: {train_loss:.4f}  "
                f"Train Acc: {train_acc:.1f}%  "
                f"Time: {elapsed:.1f}s"
            )

        # ─── Checkpointing ─────────────────────────────────────────────
        if val_auc > best_auc:
            best_auc = val_auc
            patience_counter = 0
            torch.save(model.state_dict(), save_dir / "liveness_mobilenetv3.pth")
            logger.info(f"  ✓ Saved best model (AUC={best_auc:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                logger.info(f"Early stopping at epoch {epoch+1} (patience={args.patience})")
                break

    # ─── Final report ───────────────────────────────────────────────────
    logger.info(f"\nTraining complete. Best validation AUC: {best_auc:.4f}")
    logger.info(f"Model saved to: {save_dir / 'liveness_mobilenetv3.pth'}")


# ═══════════════════════════════════════════════════════════════════════════
# ONNX Export
# ═══════════════════════════════════════════════════════════════════════════

def export_onnx(weight_path: str, output_path: str = "weights/liveness.onnx"):
    model = mobilenet_v3_small(weights=None)
    model.classifier = nn.Sequential(
        nn.Linear(576, 256),
        nn.Hardswish(),
        nn.Dropout(p=0.3),
        nn.Linear(256, 1),
        nn.Sigmoid(),
    )
    model.load_state_dict(torch.load(weight_path, map_location="cpu"))
    model.eval()

    dummy = torch.randn(1, 3, 112, 112)
    torch.onnx.export(
        model, dummy, output_path,
        input_names=["face"],
        output_names=["liveness_score"],
        dynamic_axes={"face": {0: "batch"}, "liveness_score": {0: "batch"}},
        opset_version=17,
    )
    logger.info(f"Exported to {output_path}")


# ═══════════════════════════════════════════════════════════════════════════
# INT8 Quantization
# ═══════════════════════════════════════════════════════════════════════════

def quantize_int8(onnx_path: str = "weights/liveness.onnx"):
    from onnxruntime.quantization import quantize_static, CalibrationDataReader

    class LivenessCalibReader(CalibrationDataReader):
        def __init__(self, count=100):
            self.data = [{"face": np.random.randn(1, 3, 112, 112).astype(np.float32)} for _ in range(count)]
            self.idx = 0

        def get_next(self):
            if self.idx >= len(self.data):
                return None
            r = self.data[self.idx]
            self.idx += 1
            return r

    out = onnx_path.replace(".onnx", "_int8.onnx")
    quantize_static(onnx_path, out, LivenessCalibReader())
    logger.info(f"Quantized to {out}")


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Liveness CNN")
    parser.add_argument("--data_root", type=str, default="data/liveness", help="Dataset root directory")
    parser.add_argument("--epochs", type=int, default=30, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size (increase for GPU)")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--patience", type=int, default=7, help="Early stopping patience")
    parser.add_argument("--workers", type=int, default=2, help="DataLoader workers")
    parser.add_argument("--save_dir", type=str, default="weights", help="Directory to save weights")
    parser.add_argument("--export_onnx", action="store_true", help="Export to ONNX after training")
    parser.add_argument("--quantize", action="store_true", help="INT8 quantize the ONNX model")

    args = parser.parse_args()

    train(args)

    if args.export_onnx:
        export_onnx(os.path.join(args.save_dir, "liveness_mobilenetv3.pth"))

    if args.quantize:
        quantize_int8()
