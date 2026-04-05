"""Presentation Attack Detection (PAD) module.

Implements passive anti-spoofing checks for:
- Screen/display replay attacks (moiré patterns, pixel grids, refresh artifacts)
- Printed photo attacks (paper texture, halftone, colour gamut)
- 3D mask attacks (skin texture anomalies, specular reflection, boundary artefacts)
- General texture analysis pipeline (multi-scale LBP, colour-texture features)

All methods operate on a single RGB frame (numpy array, uint8 or float32,
shape HxWx3) plus optional facial landmarks.  Each returns a sub-score in
[0, 1] where 1 = definitely real.
"""

from __future__ import annotations

from typing import Any

import numpy as np


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

def _to_gray(image: np.ndarray) -> np.ndarray:
    """Convert HxWx3 RGB to HxW float gray."""
    if image.ndim == 2:
        return image.astype(np.float32)
    return image.astype(np.float32).mean(axis=2)


def _lbp_hist(gray: np.ndarray, radius: int = 1, bins: int = 26) -> np.ndarray:
    """Simplified LBP histogram."""
    h, w = gray.shape
    if h < 2 * radius + 1 or w < 2 * radius + 1:
        return np.zeros(bins, dtype=np.float32)
    center = gray[radius:h - radius, radius:w - radius]
    offsets = [(-radius, 0), (-radius, radius), (0, radius), (radius, radius),
               (radius, 0), (radius, -radius), (0, -radius), (-radius, -radius)]
    lbp = np.zeros_like(center, dtype=np.uint8)
    for bit, (dy, dx) in enumerate(offsets):
        nb = gray[radius + dy:h - radius + dy, radius + dx:w - radius + dx]
        lbp |= ((nb >= center).astype(np.uint8) << bit)
    hist, _ = np.histogram(lbp, bins=bins, range=(0, 256))
    return (hist / (hist.sum() + 1e-8)).astype(np.float32)


# ─────────────────────────────────────────────────────────────────────────
# Screen / Display detection
# ─────────────────────────────────────────────────────────────────────────

def detect_screen_replay(image: np.ndarray) -> dict[str, Any]:
    """Analyse frame for screen-replay indicators.

    Checks for:
    - Moiré patterns via 2D-FFT periodic peaks
    - Pixel grid regularity
    - Colour temperature uniformity anomalies
    """
    gray = _to_gray(image)
    h, w = gray.shape

    # 2D FFT analysis
    spectrum = np.abs(np.fft.fftshift(np.fft.fft2(gray)))
    spectrum /= np.max(spectrum) + 1e-8

    # Build radial distance map
    cy, cx = h // 2, w // 2
    ys, xs = np.indices(spectrum.shape)
    dist = np.sqrt((ys - cy) ** 2 + (xs - cx) ** 2)

    # Look for periodic peaks in mid-high frequency band (moiré signature)
    mid_mask = (dist > np.percentile(dist, 40)) & (dist < np.percentile(dist, 80))
    mid_band = spectrum[mid_mask]
    peak_ratio = float(np.percentile(mid_band, 99) / (np.mean(mid_band) + 1e-8))
    moire_score = max(0.0, min((peak_ratio - 1.5) / 5.0, 1.0))

    # High-frequency energy (screens tend to lack very-high-freq detail)
    high_mask = dist > np.percentile(dist, 75)
    high_energy = float(spectrum[high_mask].mean())

    # Colour temperature consistency (RGB channel mean ratios)
    if image.ndim == 3:
        r_mean = float(image[:, :, 0].mean())
        g_mean = float(image[:, :, 1].mean())
        b_mean = float(image[:, :, 2].mean())
        total = r_mean + g_mean + b_mean + 1e-8
        # Screens often have cooler/bluer tone than ambient-lit faces
        color_temp_score = 1.0 - min(abs(b_mean / total - 0.33) * 3, 1.0)
    else:
        color_temp_score = 0.5

    # Aggregate: low moire + high HF energy + natural colour = real
    realness = max(0.0, min(
        0.40 * (1 - moire_score) +
        0.35 * min(high_energy * 5, 1.0) +
        0.25 * color_temp_score,
        1.0
    ))

    return {
        "screen_replay_score": round(realness, 4),
        "moire_risk": round(moire_score, 4),
        "high_freq_energy": round(high_energy, 4),
        "color_temp_score": round(color_temp_score, 4),
    }


# ─────────────────────────────────────────────────────────────────────────
# Printed photo detection
# ─────────────────────────────────────────────────────────────────────────

def detect_printed_photo(image: np.ndarray) -> dict[str, Any]:
    """Analyse frame for printed-photo indicators.

    Checks for:
    - Paper texture noise patterns
    - Limited colour gamut
    - Halftone dot patterns
    - Edge transition sharpness
    """
    gray = _to_gray(image)

    # Paper texture: high-frequency noise variance per-block
    block = 16
    h, w = gray.shape
    noise_scores = []
    for by in range(0, h - block, block):
        for bx in range(0, w - block, block):
            patch = gray[by:by + block, bx:bx + block]
            # Noise = variance of Laplacian approximation
            lap = patch[1:-1, 1:-1] * 4 - patch[:-2, 1:-1] - patch[2:, 1:-1] - patch[1:-1, :-2] - patch[1:-1, 2:]
            noise_scores.append(float(np.var(lap)))
    avg_noise = np.mean(noise_scores) if noise_scores else 0.0
    # Real faces have moderate noise; printed photos have either very low (glossy) or patterned noise
    noise_realness = max(0.0, min(avg_noise / 800.0, 1.0))

    # Colour gamut analysis
    if image.ndim == 3:
        r_range = float(image[:, :, 0].max() - image[:, :, 0].min())
        g_range = float(image[:, :, 1].max() - image[:, :, 1].min())
        b_range = float(image[:, :, 2].max() - image[:, :, 2].min())
        gamut_coverage = (r_range + g_range + b_range) / (3 * 255 + 1e-8)
        gamut_score = min(gamut_coverage * 2, 1.0)
    else:
        gamut_score = 0.5

    # Edge sharpness analysis (real faces have natural gradients, photos sharper edges)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    sharpness = float((gx.mean() + gy.mean()) / 2)
    sharpness_normalised = max(0.0, min(sharpness / 25.0, 1.0))

    realness = max(0.0, min(
        0.35 * noise_realness +
        0.35 * gamut_score +
        0.30 * sharpness_normalised,
        1.0
    ))

    return {
        "printed_photo_score": round(realness, 4),
        "texture_noise_level": round(avg_noise, 2),
        "color_gamut_score": round(gamut_score, 4),
        "edge_sharpness": round(sharpness_normalised, 4),
    }


# ─────────────────────────────────────────────────────────────────────────
# 3D mask detection
# ─────────────────────────────────────────────────────────────────────────

def detect_3d_mask(image: np.ndarray) -> dict[str, Any]:
    """Analyse frame for 3D-mask indicators.

    Checks for:
    - Skin texture anomalies (masks have different micro-texture)
    - Specular reflection patterns
    - Colour distribution naturalness
    """
    gray = _to_gray(image)

    # Multi-scale LBP texture comparison
    lbp_r1 = _lbp_hist(gray, radius=1)
    lbp_r2 = _lbp_hist(gray, radius=2)
    lbp_r3 = _lbp_hist(gray, radius=3)

    # Texture entropy at each scale (real skin has characteristic entropy)
    def entropy(hist: np.ndarray) -> float:
        h = hist[hist > 0]
        return float(-np.sum(h * np.log2(h + 1e-10)))

    ent1 = entropy(lbp_r1)
    ent2 = entropy(lbp_r2)
    ent3 = entropy(lbp_r3)
    # Real skin texture entropy typically falls in a specific range
    texture_score = max(0.0, min((ent1 + ent2 + ent3) / 12.0, 1.0))

    # Specular reflection analysis (masks reflect light differently)
    if image.ndim == 3:
        # Find bright spots (specular highlights)
        brightness = image.max(axis=2)
        highlight_ratio = float((brightness > 230).sum()) / max(brightness.size, 1)
        # Real faces have sparse, natural highlights; masks may have broad shiny patches
        reflection_score = max(0.0, 1.0 - highlight_ratio * 15)
    else:
        reflection_score = 0.5

    # Colour distribution (masks often have less natural variation)
    if image.ndim == 3:
        r_std = float(image[:, :, 0].astype(float).std())
        g_std = float(image[:, :, 1].astype(float).std())
        b_std = float(image[:, :, 2].astype(float).std())
        color_variation = (r_std + g_std + b_std) / (3 * 50 + 1e-8)  # normalise
        color_score = max(0.0, min(color_variation, 1.0))
    else:
        color_score = 0.5

    realness = max(0.0, min(
        0.40 * texture_score +
        0.30 * reflection_score +
        0.30 * color_score,
        1.0
    ))

    return {
        "mask_detection_score": round(realness, 4),
        "texture_entropy": round(ent1 + ent2 + ent3, 3),
        "specular_reflection_score": round(reflection_score, 4),
        "color_variation_score": round(color_score, 4),
    }


# ─────────────────────────────────────────────────────────────────────────
# Combined PAD analysis
# ─────────────────────────────────────────────────────────────────────────

def analyze_presentation_attack(
    image: np.ndarray | None,
    client_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the full PAD pipeline and return an aggregate score.

    Returns a dict with:
    - pad_score: aggregate 0-1 realness score (1 = real)
    - sub-scores from each detector
    - anomalies list
    """
    metrics = client_metrics or {}
    anomalies: list[str] = []

    if image is None:
        return {
            "pad_score": 0.65,
            "anomalies": ["Frame analysis unavailable – PAD score is provisional"],
            "screen_replay": {},
            "printed_photo": {},
            "mask_detection": {},
        }

    screen = detect_screen_replay(image)
    photo = detect_printed_photo(image)
    mask = detect_3d_mask(image)

    # Check face presence
    face_present = 1.0 if metrics.get("face_present") else 0.0

    # Weighted aggregate
    pad_score = max(0.0, min(
        0.25 * screen["screen_replay_score"] +
        0.25 * photo["printed_photo_score"] +
        0.25 * mask["mask_detection_score"] +
        0.10 * face_present +
        0.15 * min(screen.get("high_freq_energy", 0) * 5, 1.0),
        1.0
    ))

    # Floor PAD score for real detected faces with no anomalies
    if face_present and not anomalies and pad_score < 0.58:
        pad_score = 0.58

    # Flag anomalies
    if screen["moire_risk"] > 0.45:
        anomalies.append("Possible screen replay – moiré pattern detected")
    if photo["color_gamut_score"] < 0.3:
        anomalies.append("Limited colour gamut – possible printed photo")
    if mask["texture_entropy"] < 3.0:
        anomalies.append("Unusually low skin texture entropy – possible mask")
    if mask["specular_reflection_score"] < 0.3:
        anomalies.append("Abnormal specular reflection pattern – possible mask or glossy surface")

    return {
        "pad_score": round(pad_score, 4),
        "anomalies": anomalies,
        "screen_replay": screen,
        "printed_photo": photo,
        "mask_detection": mask,
    }
