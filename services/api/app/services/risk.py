"""Risk analysis orchestrator — delegates to PAD and deepfake detectors.

This module provides the top-level API for frame-level risk assessment,
combining presentation-attack detection and deepfake detection results.
"""

from __future__ import annotations

import base64
import io
from typing import Any

import numpy as np
from PIL import Image

from .pad_detector import analyze_presentation_attack
from .deepfake_detector import (
    TemporalAnalyzer,
    RPPGAnalyzer,
    analyze_deepfake_risk,
)


def _decode_frame(frame_b64: str | None) -> np.ndarray | None:
    """Decode a base64-encoded JPEG/PNG frame to a numpy array."""
    if not frame_b64:
        return None
    if "," in frame_b64:
        frame_b64 = frame_b64.split(",", 1)[1]
    try:
        raw = base64.b64decode(frame_b64)
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        return np.asarray(image, dtype=np.float32)
    except Exception:
        return None


def analyze_frame_risk(
    frame_b64: str | None = None,
    landmarks: list[list[float]] | None = None,
    client_metrics: dict[str, Any] | None = None,
    temporal_analyzer: TemporalAnalyzer | None = None,
    rppg_analyzer: RPPGAnalyzer | None = None,
    embedding: list[float] | None = None,
) -> dict[str, Any]:
    """Comprehensive frame-level risk assessment.

    Combines:
    - Presentation-attack detection (screen/photo/mask)
    - Deepfake detection (frequency/boundary/eye/mouth/temporal/rPPG)
    - Image quality metrics (sharpness, exposure)

    Returns a dict with pad_score, deepfake_score, quality_score, etc.
    """
    image = _decode_frame(frame_b64)
    metrics = client_metrics or {}
    anomalies: list[str] = []
    guidance: list[str] = []

    # ── PAD analysis ──
    pad_result = analyze_presentation_attack(image, metrics)

    # ── Update temporal and rPPG analysers ──
    temporal_scores = None
    rppg_scores = None

    if temporal_analyzer and image is not None:
        temporal_analyzer.update(
            landmarks=landmarks,
            embedding=embedding,
            image=image,
        )
        temporal_scores = temporal_analyzer.update(landmarks, embedding, image)

    if rppg_analyzer and image is not None:
        rppg_analyzer.add_frame(image, landmarks)
        rppg_scores = rppg_analyzer.analyze()

    # ── Deepfake analysis ──
    deepfake_result = analyze_deepfake_risk(
        image, landmarks, metrics, temporal_scores, rppg_scores
    )

    # ── Image quality metrics ──
    if image is not None:
        gray = image.mean(axis=2) if image.ndim == 3 else image
        gx = np.abs(np.diff(gray, axis=1)).mean()
        gy = np.abs(np.diff(gray, axis=0)).mean()
        sharpness = max(0.0, min(float((gx + gy) / 50), 1.0))
        exposure = float(gray.mean() / 255.0)
        quality_score = (0.5 * sharpness + 0.5 * (1 - abs(exposure - 0.5))) * 100

        if sharpness < 0.3:
            guidance.append("Image is blurry – hold the camera steady")
        if exposure < 0.25:
            guidance.append("Image is too dark – improve lighting")
        elif exposure > 0.75:
            guidance.append("Image is overexposed – reduce light intensity")
    else:
        sharpness = 0.5
        exposure = 0.5
        quality_score = 55.0
        guidance.append("Frame unavailable")

    # Merge anomalies
    anomalies.extend(pad_result.get("anomalies", []))
    anomalies.extend(deepfake_result.get("anomalies", []))

    if not guidance:
        guidance.append("Capture quality is acceptable")

    return {
        "pad_score": pad_result["pad_score"],
        "deepfake_score": deepfake_result["deepfake_score"],
        "quality_score": round(quality_score, 2),
        "sharpness": round(sharpness, 4),
        "exposure": round(exposure, 4),
        "guidance": guidance,
        "anomalies": anomalies,
        "pad_detail": pad_result,
        "deepfake_detail": deepfake_result,
    }
