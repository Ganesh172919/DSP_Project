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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(value, high))


def _framing_score(metrics: dict[str, Any]) -> float:
    if not metrics.get("face_present"):
        return 0.0

    face_size_ratio = float(metrics.get("face_size_ratio") or 0.0)
    pitch = abs(float(metrics.get("pitch") or 0.0))
    roll = abs(float(metrics.get("roll") or 0.0))
    hand_near_face = bool(metrics.get("hand_near_face"))
    quality_hint = str(metrics.get("quality_hint") or "")

    size_score = _clamp((face_size_ratio - 0.04) / 0.10)
    pose_score = 1.0 - min(1.0, (roll / 30.0) * 0.7 + (pitch / 25.0) * 0.3)
    occlusion_score = 0.55 if hand_near_face else 1.0
    hint_score = 1.0 if quality_hint == "Ready" else 0.75

    return _clamp(
        0.45 * size_score +
        0.25 * pose_score +
        0.15 * occlusion_score +
        0.15 * hint_score
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
    framing = _framing_score(metrics)
    if image is not None:
        gray = image.mean(axis=2) if image.ndim == 3 else image
        gx = np.abs(np.diff(gray, axis=1)).mean()
        gy = np.abs(np.diff(gray, axis=0)).mean()
        sharpness = _clamp(float((gx + gy) / 12.0))
        exposure = float(gray.mean() / 255.0)
        exposure_score = _clamp(1 - abs(exposure - 0.5) * 1.8)
        quality_score = (
            0.45 * sharpness +
            0.30 * exposure_score +
            0.25 * framing
        ) * 100

        if sharpness < 0.3:
            guidance.append("Image is blurry – hold the camera steady")
        if exposure < 0.25:
            guidance.append("Image is too dark – improve lighting")
        elif exposure > 0.75:
            guidance.append("Image is overexposed – reduce light intensity")
    else:
        sharpness = 0.5
        exposure = 0.5
        quality_score = 45.0 + framing * 25.0
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
        "framing": round(framing, 4),
        "guidance": guidance,
        "anomalies": anomalies,
        "pad_detail": pad_result,
        "deepfake_detail": deepfake_result,
    }
