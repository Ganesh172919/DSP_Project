"""
evaluate.py — FAR / FRR / AUC / ms-per-frame Benchmark Script

Evaluates all models in the pipeline on test data and produces a
comprehensive performance report.

Metrics:
  - FAR (False Accept Rate)   — spoof/fake accepted as live/real
  - FRR (False Reject Rate)   — live/real rejected as spoof/fake
  - AUC-ROC
  - Precision, Recall, F1
  - Inference time (ms/frame) on CPU

Usage:
  python -m training.evaluate --data_root data/test --model all
"""

import argparse
import logging
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from sklearn.metrics import (
    roc_auc_score, roc_curve, precision_score, recall_score,
    f1_score, classification_report, confusion_matrix,
)
from torchvision import transforms
from torchvision.models import mobilenet_v3_small, efficientnet_b4

from training.train_liveness import LivenessDataset
from training.train_deepfake import DeepfakeDataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)


def compute_far_frr(y_true: np.ndarray, y_scores: np.ndarray, threshold: float):
    """
    Compute False Accept Rate (FAR) and False Reject Rate (FRR).

    FAR  = FP / (FP + TN) — proportion of negatives incorrectly accepted
    FRR  = FN / (FN + TP) — proportion of positives incorrectly rejected
    """
    predicted = (y_scores >= threshold).astype(int)

    tp = np.sum((predicted == 1) & (y_true == 1))
    fp = np.sum((predicted == 1) & (y_true == 0))
    tn = np.sum((predicted == 0) & (y_true == 0))
    fn = np.sum((predicted == 0) & (y_true == 1))

    far = fp / max(fp + tn, 1)
    frr = fn / max(fn + tp, 1)

    return far, frr


def find_eer(y_true: np.ndarray, y_scores: np.ndarray):
    """Find Equal Error Rate (EER) — threshold where FAR = FRR."""
    fpr, tpr, thresholds = roc_curve(y_true, y_scores)
    fnr = 1 - tpr

    # Find closest point where FPR ≈ FNR
    idx = np.nanargmin(np.abs(fpr - fnr))
    eer = (fpr[idx] + fnr[idx]) / 2
    eer_threshold = thresholds[idx]

    return eer, eer_threshold


def benchmark_inference(model, input_shape, num_runs=100, device="cpu"):
    """Benchmark model inference time."""
    model = model.to(device)
    model.eval()
    dummy = torch.randn(*input_shape).to(device)

    # Warmup
    with torch.no_grad():
        for _ in range(10):
            model(dummy)

    times = []
    with torch.no_grad():
        for _ in range(num_runs):
            t0 = time.perf_counter()
            model(dummy)
            times.append((time.perf_counter() - t0) * 1000)

    times = np.array(times)
    return {
        "mean_ms": float(times.mean()),
        "median_ms": float(np.median(times)),
        "p95_ms": float(np.percentile(times, 95)),
        "p99_ms": float(np.percentile(times, 99)),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Evaluate Liveness Model
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_liveness(args):
    """Evaluate MobileNetV3-Small liveness model."""
    logger.info("\n" + "=" * 60)
    logger.info("LIVENESS MODEL EVALUATION (MobileNetV3-Small)")
    logger.info("=" * 60)

    device = torch.device("cpu")

    model = mobilenet_v3_small(weights=None)
    model.classifier = nn.Sequential(
        nn.Linear(576, 256), nn.Hardswish(), nn.Dropout(0.3),
        nn.Linear(256, 1), nn.Sigmoid(),
    )

    weight_path = Path(args.weights_dir) / "liveness_mobilenetv3.pth"
    if weight_path.exists():
        model.load_state_dict(torch.load(str(weight_path), map_location=device))
        logger.info(f"Loaded weights: {weight_path}")
    else:
        logger.warning(f"Weights not found: {weight_path} — using random init")

    model.eval()

    val_transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    test_data = LivenessDataset(args.data_root, "val", val_transform)
    if len(test_data) == 0:
        logger.warning("No test data found for liveness evaluation")
        return

    loader = DataLoader(test_data, batch_size=32, shuffle=False, num_workers=2)

    all_preds, all_labels = [], []
    with torch.no_grad():
        for images, labels in loader:
            outputs = model(images).squeeze(-1)
            all_preds.extend(outputs.numpy())
            all_labels.extend(labels.numpy())

    y_true = np.array(all_labels)
    y_scores = np.array(all_preds)

    # Metrics at threshold = 0.85
    threshold = 0.85
    auc = roc_auc_score(y_true, y_scores)
    far, frr = compute_far_frr(y_true, y_scores, threshold)
    eer, eer_thresh = find_eer(y_true, y_scores)

    binary_preds = (y_scores >= threshold).astype(int)
    precision = precision_score(y_true, binary_preds, zero_division=0)
    recall = recall_score(y_true, binary_preds, zero_division=0)
    f1 = f1_score(y_true, binary_preds, zero_division=0)

    # Inference speed
    timing = benchmark_inference(model, (1, 3, 112, 112))

    logger.info(f"\nThreshold: {threshold}")
    logger.info(f"AUC-ROC:         {auc:.4f}")
    logger.info(f"FAR:             {far:.4f}")
    logger.info(f"FRR:             {frr:.4f}")
    logger.info(f"EER:             {eer:.4f} (at threshold={eer_thresh:.4f})")
    logger.info(f"Precision:       {precision:.4f}")
    logger.info(f"Recall:          {recall:.4f}")
    logger.info(f"F1-Score:        {f1:.4f}")
    logger.info(f"\nInference Speed (CPU):")
    logger.info(f"  Mean:   {timing['mean_ms']:.2f} ms/frame")
    logger.info(f"  Median: {timing['median_ms']:.2f} ms/frame")
    logger.info(f"  P95:    {timing['p95_ms']:.2f} ms/frame")
    logger.info(f"  P99:    {timing['p99_ms']:.2f} ms/frame")

    logger.info(f"\n{classification_report(y_true, binary_preds, target_names=['Spoof', 'Live'], zero_division=0)}")

    return {"auc": auc, "far": far, "frr": frr, "eer": eer, "f1": f1, "timing": timing}


# ═══════════════════════════════════════════════════════════════════════════
# Evaluate Deepfake Model
# ═══════════════════════════════════════════════════════════════════════════

def evaluate_deepfake(args):
    """Evaluate EfficientNet-B4 deepfake detector."""
    logger.info("\n" + "=" * 60)
    logger.info("DEEPFAKE DETECTION EVALUATION (EfficientNet-B4)")
    logger.info("=" * 60)

    device = torch.device("cpu")

    try:
        from efficientnet_pytorch import EfficientNet
        model = EfficientNet.from_name("efficientnet-b4", num_classes=1)
    except ImportError:
        model = efficientnet_b4(weights=None)
        model.classifier = nn.Sequential(nn.Dropout(0.4), nn.Linear(1792, 1))

    weight_path = Path(args.weights_dir) / "deepfake_efficientnet_b4.pth"
    if weight_path.exists():
        model.load_state_dict(torch.load(str(weight_path), map_location=device))
        logger.info(f"Loaded weights: {weight_path}")
    else:
        logger.warning(f"Weights not found: {weight_path}")

    model.eval()

    val_transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    test_data = DeepfakeDataset(args.data_root, "val", val_transform)
    if len(test_data) == 0:
        logger.warning("No test data found for deepfake evaluation")
        return

    loader = DataLoader(test_data, batch_size=16, shuffle=False, num_workers=2)

    all_preds, all_labels = [], []
    with torch.no_grad():
        for images, labels in loader:
            logits = model(images).squeeze(-1)
            probs = torch.sigmoid(logits)
            all_preds.extend(probs.numpy())
            all_labels.extend(labels.numpy())

    y_true = np.array(all_labels)
    y_scores = np.array(all_preds)

    threshold = 0.30
    auc = roc_auc_score(y_true, y_scores)
    far, frr = compute_far_frr(y_true, y_scores, threshold)
    eer, eer_thresh = find_eer(y_true, y_scores)

    binary_preds = (y_scores >= threshold).astype(int)
    precision = precision_score(y_true, binary_preds, zero_division=0)
    recall = recall_score(y_true, binary_preds, zero_division=0)
    f1 = f1_score(y_true, binary_preds, zero_division=0)

    timing = benchmark_inference(model, (1, 3, 224, 224))

    logger.info(f"\nThreshold: {threshold}")
    logger.info(f"AUC-ROC:         {auc:.4f}")
    logger.info(f"FAR:             {far:.4f}")
    logger.info(f"FRR:             {frr:.4f}")
    logger.info(f"EER:             {eer:.4f} (at threshold={eer_thresh:.4f})")
    logger.info(f"Precision:       {precision:.4f}")
    logger.info(f"Recall:          {recall:.4f}")
    logger.info(f"F1-Score:        {f1:.4f}")
    logger.info(f"\nInference Speed (CPU):")
    logger.info(f"  Mean:   {timing['mean_ms']:.2f} ms/frame")
    logger.info(f"  Median: {timing['median_ms']:.2f} ms/frame")
    logger.info(f"  P95:    {timing['p95_ms']:.2f} ms/frame")
    logger.info(f"  P99:    {timing['p99_ms']:.2f} ms/frame")

    logger.info(f"\n{classification_report(y_true, binary_preds, target_names=['Real', 'Fake'], zero_division=0)}")

    # ─── Benchmark Results Table ────────────────────────────────────────
    logger.info("\n┌────────────────────────────────────────────────────┐")
    logger.info("│       DEEPFAKE DETECTION BENCHMARK SUMMARY        │")
    logger.info("├─────────────────┬─────────────────┬───────────────┤")
    logger.info("│ Metric          │ Value           │ Threshold     │")
    logger.info("├─────────────────┼─────────────────┼───────────────┤")
    logger.info(f"│ AUC-ROC         │ {auc:>15.4f} │               │")
    logger.info(f"│ Precision       │ {precision:>15.4f} │ {threshold:>13.2f} │")
    logger.info(f"│ Recall          │ {recall:>15.4f} │ {threshold:>13.2f} │")
    logger.info(f"│ F1-Score        │ {f1:>15.4f} │ {threshold:>13.2f} │")
    logger.info(f"│ FAR             │ {far:>15.4f} │ {threshold:>13.2f} │")
    logger.info(f"│ FRR             │ {frr:>15.4f} │ {threshold:>13.2f} │")
    logger.info(f"│ EER             │ {eer:>15.4f} │ {eer_thresh:>13.4f} │")
    logger.info(f"│ ms/frame (mean) │ {timing['mean_ms']:>12.2f} ms │ CPU           │")
    logger.info(f"│ ms/frame (p95)  │ {timing['p95_ms']:>12.2f} ms │ CPU           │")
    logger.info("└─────────────────┴─────────────────┴───────────────┘")

    return {"auc": auc, "far": far, "frr": frr, "eer": eer, "f1": f1, "timing": timing}


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Face Auth Models")
    parser.add_argument("--data_root", type=str, default="data/test")
    parser.add_argument("--weights_dir", type=str, default="weights")
    parser.add_argument("--model", type=str, default="all",
                        choices=["liveness", "deepfake", "all"])

    args = parser.parse_args()

    results = {}
    if args.model in ("liveness", "all"):
        results["liveness"] = evaluate_liveness(args)

    if args.model in ("deepfake", "all"):
        results["deepfake"] = evaluate_deepfake(args)

    logger.info("\n" + "=" * 60)
    logger.info("ALL EVALUATIONS COMPLETE")
    logger.info("=" * 60)
