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


def _ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _guidance_from_metrics(metrics: dict[str, Any]) -> list[str]:
    if not metrics.get("face_present"):
        return ["Place your face inside the guide"]

    guidance: list[str] = []
    face_size_ratio = float(metrics.get("face_size_ratio") or 0.0)
    face_center_x = float(metrics.get("face_center_x") or 0.5)
    eye_line_y = float(metrics.get("eye_line_y") or metrics.get("face_center_y") or 0.5)
    face_top_margin = float(metrics.get("face_top_margin") or 0.0)
    face_bottom_margin = float(metrics.get("face_bottom_margin") or 0.0)
    roll = abs(float(metrics.get("roll") or 0.0))
    quality_hint = str(metrics.get("quality_hint") or "")

    if face_size_ratio < 0.05:
        guidance.append("Move closer to the camera")
    if eye_line_y > 0.50 or face_bottom_margin < 0.05:
        guidance.append("Raise the camera or tilt your screen upward")
    elif eye_line_y < 0.15 or face_top_margin < 0.02:
        guidance.append("Lower the camera slightly")
    if face_center_x < 0.30:
        guidance.append("Move your face to the right")
    elif face_center_x > 0.70:
        guidance.append("Move your face to the left")
    if roll > 15.0:
        guidance.append("Straighten your head")
    if quality_hint and quality_hint not in {"Ready", "No face"}:
        guidance.append(quality_hint)

    return _ordered_unique(guidance)


def _framing_score(metrics: dict[str, Any]) -> float:
    if not metrics.get("face_present"):
        return 0.0

    face_size_ratio = float(metrics.get("face_size_ratio") or 0.0)
    pitch = abs(float(metrics.get("pitch") or 0.0))
    roll = abs(float(metrics.get("roll") or 0.0))
    face_center_x = float(metrics.get("face_center_x") or 0.5)
    eye_line_y = float(metrics.get("eye_line_y") or metrics.get("face_center_y") or 0.5)
    face_top_margin = float(metrics.get("face_top_margin") or 0.0)
    face_bottom_margin = float(metrics.get("face_bottom_margin") or 0.0)
    hand_near_face = bool(metrics.get("hand_near_face"))
    quality_hint = str(metrics.get("quality_hint") or "")

    # More forgiving size requirement
    size_score = _clamp((face_size_ratio - 0.03) / 0.10)
    pose_score = 1.0 - min(1.0, (roll / 30.0) * 0.55 + (pitch / 35.0) * 0.45)
    center_score = _clamp(1.0 - abs(face_center_x - 0.5) / 0.25)
    # Laptop webcams place the face lower — use 0.40 as ideal eye-line
    eye_line_score = _clamp(1.0 - abs(eye_line_y - 0.40) / 0.24)
    margin_score = _clamp(min(face_top_margin, face_bottom_margin) / 0.05)
    alignment_score = _clamp(0.40 * center_score + 0.35 * eye_line_score + 0.25 * margin_score)
    occlusion_score = 0.65 if hand_near_face else 1.0
    hint_score = 1.0 if quality_hint == "Ready" else 0.78

    return _clamp(
        0.28 * size_score +
        0.18 * pose_score +
        0.26 * alignment_score +
        0.14 * occlusion_score +
        0.14 * hint_score
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
    guidance = _guidance_from_metrics(metrics)

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
            0.40 * sharpness +
            0.25 * exposure_score +
            0.35 * framing
        ) * 100
        # Floor quality at 40 if face is present (prevent score collapse)
        if metrics.get("face_present") and quality_score < 40.0:
            quality_score = 40.0 + quality_score * 0.3

        if sharpness < 0.25:
            guidance.append("Image is blurry – hold the camera steady")
        if exposure < 0.20:
            guidance.append("Image is too dark – improve lighting")
        elif exposure > 0.80:
            guidance.append("Image is overexposed – reduce light intensity")
    else:
        sharpness = 0.5
        exposure = 0.5
        quality_score = 55.0 + framing * 20.0
        if not guidance:
            guidance.append("Frame data not available – using landmark-only analysis")

    # Merge anomalies
    anomalies.extend(pad_result.get("anomalies", []))
    anomalies.extend(deepfake_result.get("anomalies", []))
    guidance = _ordered_unique(guidance)

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
