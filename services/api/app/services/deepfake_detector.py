"""Deepfake detection engine.

Implements multi-modal deepfake detection:
1. Frequency-domain analysis (DFT spectrum, power spectrum, HFER)
2. Face boundary analysis (edge consistency, resolution uniformity)
3. Temporal consistency (frame-to-frame jitter, embedding stability)
4. Eye/reflection analysis (corneal specular consistency, pupil shape)
5. Teeth/mouth interior analysis (when mouth is open)
6. Remote photoplethysmography (rPPG) for pulse signal extraction

All heuristic-based – designed for plug-in replacement with trained models
(EfficientNet, XceptionNet, ViT) when available.
"""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np


# ─────────────────────────────────────────────────────────────────────────
# Method 1: Frequency domain analysis
# ─────────────────────────────────────────────────────────────────────────

def frequency_domain_analysis(image: np.ndarray) -> dict[str, float]:
    """Analyse the frequency spectrum of a face image for deepfake artifacts.

    GAN-generated faces often:
    - Lack high-frequency detail present in real camera captures
    - Show periodic patterns from up-sampling layers
    - Deviate from the natural 1/f power-spectrum falloff
    """
    gray = image.mean(axis=2) if image.ndim == 3 else image.astype(np.float32)
    h, w = gray.shape

    # 2D FFT
    spectrum = np.abs(np.fft.fftshift(np.fft.fft2(gray)))
    spectrum /= np.max(spectrum) + 1e-8

    # Build radial distance map
    cy, cx = h // 2, w // 2
    ys, xs = np.indices(spectrum.shape)
    dist = np.sqrt((ys - cy) ** 2 + (xs - cx) ** 2)
    max_radius = min(cy, cx)

    # Azimuthally averaged power spectrum
    n_bins = min(64, max_radius)
    radii = np.linspace(0, max_radius, n_bins + 1)
    power_profile = np.zeros(n_bins)
    for i in range(n_bins):
        mask = (dist >= radii[i]) & (dist < radii[i + 1])
        if mask.any():
            power_profile[i] = float(spectrum[mask].mean())

    # 1/f falloff check: fit log-log slope (real images ≈ -1 to -2)
    valid = power_profile > 0
    if valid.sum() > 5:
        log_r = np.log(np.arange(1, n_bins + 1)[valid])
        log_p = np.log(power_profile[valid])
        slope = float(np.polyfit(log_r, log_p, 1)[0])
    else:
        slope = -1.0
    # Real images: slope ≈ -1.5; deepfakes often flatter (closer to 0)
    slope_score = max(0.0, min((-slope - 0.3) / 2.0, 1.0))

    # High-Frequency Energy Ratio (HFER)
    hf_mask = dist > np.percentile(dist, 70)
    lf_mask = dist < np.percentile(dist, 30)
    hfer = float(spectrum[hf_mask].mean() / (spectrum[lf_mask].mean() + 1e-8))
    hfer_score = max(0.0, min(hfer * 3, 1.0))

    # Periodicity detection (GAN fingerprint)
    mid_mask = (dist > np.percentile(dist, 35)) & (dist < np.percentile(dist, 70))
    mid_band = spectrum[mid_mask]
    peak_ratio = float(np.percentile(mid_band, 99) / (np.mean(mid_band) + 1e-8))
    periodicity_clean = max(0.0, 1.0 - min((peak_ratio - 2.0) / 5.0, 1.0))

    realness = (0.35 * slope_score + 0.35 * hfer_score + 0.30 * periodicity_clean)

    return {
        "frequency_score": round(max(0.0, min(realness, 1.0)), 4),
        "spectrum_slope": round(slope, 3),
        "hfer": round(hfer, 4),
        "periodicity_clean": round(periodicity_clean, 4),
    }


# ─────────────────────────────────────────────────────────────────────────
# Method 2: Face boundary analysis
# ─────────────────────────────────────────────────────────────────────────

def face_boundary_analysis(image: np.ndarray, landmarks: list[list[float]] | None = None) -> dict[str, float]:
    """Check for blending artefacts at the face boundary.

    Deepfake face swaps create a blending seam where the synthetic face
    meets the original image.
    """
    gray = image.mean(axis=2) if image.ndim == 3 else image.astype(np.float32)
    h, w = gray.shape

    # Approximate face boundary using landmark extremes or image center
    if landmarks and len(landmarks) > 100:
        pts = np.array(landmarks, dtype=np.float32)
        xs = (pts[:, 0] * w).astype(int).clip(0, w - 1)
        ys = (pts[:, 1] * h).astype(int).clip(0, h - 1)
        face_x_min, face_x_max = int(xs.min()), int(xs.max())
        face_y_min, face_y_max = int(ys.min()), int(ys.max())
    else:
        face_x_min, face_x_max = w // 4, 3 * w // 4
        face_y_min, face_y_max = h // 4, 3 * h // 4

    # Extract a band around the face boundary
    margin = max(5, (face_x_max - face_x_min) // 10)

    # Edge magnitude along the boundary (using Sobel-like gradient)
    gx = np.abs(np.diff(gray, axis=1))
    gy = np.abs(np.diff(gray, axis=0))
    edge_mag = np.zeros_like(gray)
    edge_mag[:, :-1] += gx
    edge_mag[:-1, :] += gy

    # Compare edge magnitude inside boundary band vs face interior
    boundary_mask = np.zeros((h, w), dtype=bool)
    yy, xx = np.indices((h, w))
    boundary_mask |= (np.abs(xx - face_x_min) < margin) & (yy >= face_y_min) & (yy <= face_y_max)
    boundary_mask |= (np.abs(xx - face_x_max) < margin) & (yy >= face_y_min) & (yy <= face_y_max)
    boundary_mask |= (np.abs(yy - face_y_min) < margin) & (xx >= face_x_min) & (xx <= face_x_max)
    boundary_mask |= (np.abs(yy - face_y_max) < margin) & (xx >= face_x_min) & (xx <= face_x_max)

    interior_mask = (xx > face_x_min + margin) & (xx < face_x_max - margin) & \
                    (yy > face_y_min + margin) & (yy < face_y_max - margin)

    boundary_edge = float(edge_mag[boundary_mask].mean()) if boundary_mask.any() else 0
    interior_edge = float(edge_mag[interior_mask].mean()) if interior_mask.any() else 1

    # High boundary-to-interior edge ratio suggests blending artefact
    edge_ratio = boundary_edge / (interior_edge + 1e-8)
    # Real faces: ratio ≈ 1; blended deepfakes: ratio >> 1
    boundary_score = max(0.0, min(1.0 - (edge_ratio - 1.0) * 0.5, 1.0))

    # Resolution consistency check
    if image.ndim == 3:
        face_region = image[face_y_min:face_y_max, face_x_min:face_x_max]
        outer_top = image[:face_y_min, :] if face_y_min > 20 else image[:20, :]
        face_sharpness = float(np.abs(np.diff(face_region.mean(axis=2), axis=1)).mean())
        outer_sharpness = float(np.abs(np.diff(outer_top.mean(axis=2), axis=1)).mean()) if outer_top.size > 100 else face_sharpness
        resolution_ratio = face_sharpness / (outer_sharpness + 1e-8)
        # Very mismatched sharpness suggests pasted face
        resolution_score = max(0.0, min(1.0 - abs(resolution_ratio - 1.0) * 0.5, 1.0))
    else:
        resolution_score = 0.5

    realness = 0.55 * boundary_score + 0.45 * resolution_score

    return {
        "boundary_score": round(max(0.0, min(realness, 1.0)), 4),
        "edge_ratio": round(edge_ratio, 3),
        "resolution_consistency": round(resolution_score, 4),
    }


# ─────────────────────────────────────────────────────────────────────────
# Method 3: Temporal consistency analysis
# ─────────────────────────────────────────────────────────────────────────

class TemporalAnalyzer:
    """Stateful analyser that tracks frame-to-frame consistency."""

    def __init__(self, window: int = 30):
        self.window = window
        self.landmark_history: deque[np.ndarray] = deque(maxlen=window)
        self.embedding_history: deque[np.ndarray] = deque(maxlen=window)
        self.brightness_history: deque[float] = deque(maxlen=window)

    def update(
        self,
        landmarks: list[list[float]] | None = None,
        embedding: list[float] | None = None,
        image: np.ndarray | None = None,
    ) -> dict[str, float]:
        """Add a new frame observation and return temporal consistency scores."""
        if landmarks:
            self.landmark_history.append(np.array(landmarks, dtype=np.float32))
        if embedding:
            self.embedding_history.append(np.array(embedding, dtype=np.float32))
        if image is not None:
            gray = image.mean(axis=2) if image.ndim == 3 else image
            self.brightness_history.append(float(gray.mean()))

        scores: dict[str, float] = {}

        # Landmark jitter (unnatural micro-movements)
        if len(self.landmark_history) >= 3:
            diffs = []
            for i in range(1, len(self.landmark_history)):
                prev = self.landmark_history[i - 1]
                curr = self.landmark_history[i]
                if prev.shape == curr.shape:
                    diffs.append(float(np.mean(np.abs(curr - prev))))
            if diffs:
                jitter = float(np.std(diffs))
                # Very high or very low jitter is suspicious
                # Real faces have moderate, consistent jitter
                jitter_score = max(0.0, 1.0 - abs(jitter - 0.002) * 200)
                scores["landmark_jitter_score"] = round(max(0.0, min(jitter_score, 1.0)), 4)

        # Embedding stability (real faces change smoothly)
        if len(self.embedding_history) >= 3:
            emb_diffs = []
            for i in range(1, len(self.embedding_history)):
                cos_sim = float(np.dot(self.embedding_history[i - 1], self.embedding_history[i]) /
                              (np.linalg.norm(self.embedding_history[i - 1]) *
                               np.linalg.norm(self.embedding_history[i]) + 1e-8))
                emb_diffs.append(cos_sim)
            stability = float(np.mean(emb_diffs))
            scores["embedding_stability"] = round(max(0.0, min(stability, 1.0)), 4)

        # Brightness consistency
        if len(self.brightness_history) >= 5:
            brightness_std = float(np.std(list(self.brightness_history)))
            # Extremely stable brightness suggests screen source
            if brightness_std < 0.5:
                scores["brightness_stability_flag"] = 0.3
            else:
                scores["brightness_stability_flag"] = round(min(brightness_std / 5.0, 1.0), 4)

        return scores

    def reset(self) -> None:
        self.landmark_history.clear()
        self.embedding_history.clear()
        self.brightness_history.clear()


# ─────────────────────────────────────────────────────────────────────────
# Method 4: Eye and reflection analysis
# ─────────────────────────────────────────────────────────────────────────

def eye_reflection_analysis(image: np.ndarray, landmarks: list[list[float]] | None = None) -> dict[str, float]:
    """Check for consistent corneal specular reflections.

    Real faces show matching light-source reflections in both eyes.
    Deepfakes may generate inconsistent eye reflections.
    """
    if image.ndim != 3 or landmarks is None or len(landmarks) < 474:
        return {"eye_reflection_score": 0.5}

    h, w = image.shape[:2]
    pts = np.array(landmarks, dtype=np.float32)

    # Left and right iris regions
    left_iris_indices = [468, 469, 470, 471, 472]
    right_iris_indices = [473, 474, 475, 476, 477]

    def _extract_eye_patch(indices: list[int]) -> np.ndarray | None:
        eye_pts = pts[indices]
        xs = (eye_pts[:, 0] * w).astype(int).clip(0, w - 1)
        ys = (eye_pts[:, 1] * h).astype(int).clip(0, h - 1)
        x_min, x_max = max(xs.min() - 3, 0), min(xs.max() + 3, w)
        y_min, y_max = max(ys.min() - 3, 0), min(ys.max() + 3, h)
        if x_max - x_min < 3 or y_max - y_min < 3:
            return None
        return image[y_min:y_max, x_min:x_max]

    left_patch = _extract_eye_patch(left_iris_indices)
    right_patch = _extract_eye_patch(right_iris_indices)

    if left_patch is None or right_patch is None:
        return {"eye_reflection_score": 0.5}

    # Compare specular highlight patterns
    left_brightness = left_patch.max(axis=2)
    right_brightness = right_patch.max(axis=2)

    # Find bright spots (specular reflections)
    left_highlight_ratio = float((left_brightness > 200).sum()) / max(left_brightness.size, 1)
    right_highlight_ratio = float((right_brightness > 200).sum()) / max(right_brightness.size, 1)

    # Similar highlight ratio in both eyes suggests consistent lighting (real face)
    highlight_diff = abs(left_highlight_ratio - right_highlight_ratio)
    reflection_consistency = max(0.0, 1.0 - highlight_diff * 10)

    # Eye region colour consistency
    left_mean_color = left_patch.mean(axis=(0, 1))
    right_mean_color = right_patch.mean(axis=(0, 1))
    color_diff = float(np.linalg.norm(left_mean_color - right_mean_color)) / 255
    color_consistency = max(0.0, 1.0 - color_diff * 3)

    score = 0.5 * reflection_consistency + 0.5 * color_consistency

    return {
        "eye_reflection_score": round(max(0.0, min(score, 1.0)), 4),
        "reflection_consistency": round(reflection_consistency, 4),
        "eye_color_consistency": round(color_consistency, 4),
    }


# ─────────────────────────────────────────────────────────────────────────
# Method 5: Teeth/mouth interior analysis
# ─────────────────────────────────────────────────────────────────────────

def mouth_interior_analysis(
    image: np.ndarray,
    landmarks: list[list[float]] | None = None,
    mar: float = 0.0,
) -> dict[str, float]:
    """Analyse mouth interior when open (teeth, tongue naturalness).

    Deepfakes often generate blurry/deformed teeth.
    """
    if image.ndim != 3 or landmarks is None or len(landmarks) < 300 or mar < 0.15:
        return {"mouth_interior_score": 0.5}  # Mouth not open enough to analyse

    h, w = image.shape[:2]
    pts = np.array(landmarks, dtype=np.float32)

    # Mouth region extraction
    mouth_indices = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308,
                     95, 88, 178, 87, 14, 317, 402, 318, 324]
    mouth_pts = pts[[i for i in mouth_indices if i < len(pts)]]
    if len(mouth_pts) < 5:
        return {"mouth_interior_score": 0.5}

    xs = (mouth_pts[:, 0] * w).astype(int).clip(0, w - 1)
    ys = (mouth_pts[:, 1] * h).astype(int).clip(0, h - 1)
    x_min, x_max = max(xs.min(), 0), min(xs.max(), w)
    y_min, y_max = max(ys.min(), 0), min(ys.max(), h)
    if x_max - x_min < 5 or y_max - y_min < 5:
        return {"mouth_interior_score": 0.5}

    mouth_patch = image[y_min:y_max, x_min:x_max]

    # Teeth detection: bright pixels within the mouth region
    brightness = mouth_patch.max(axis=2)
    teeth_ratio = float((brightness > 180).sum()) / max(brightness.size, 1)

    # Interior darkness (mouth interior should generally be darker than face)
    interior_brightness = float(mouth_patch.mean())
    # Midface comparison
    face_brightness = float(image[h // 4:3 * h // 4, w // 4:3 * w // 4].mean())
    darkness_ratio = interior_brightness / (face_brightness + 1e-8)

    # Real mouths are darker inside with clear teeth contrast
    darkness_score = max(0.0, min((1.0 - darkness_ratio) * 2, 1.0))

    # Texture detail in mouth region
    gray_mouth = mouth_patch.mean(axis=2)
    gx = np.abs(np.diff(gray_mouth, axis=1))
    texture_detail = float(gx.mean()) / 15
    texture_score = max(0.0, min(texture_detail, 1.0))

    score = 0.35 * darkness_score + 0.35 * texture_score + 0.30 * min(teeth_ratio * 5, 1.0)

    return {
        "mouth_interior_score": round(max(0.0, min(score, 1.0)), 4),
        "teeth_visibility": round(teeth_ratio, 4),
        "interior_darkness": round(darkness_ratio, 4),
    }


# ─────────────────────────────────────────────────────────────────────────
# Method 6: Remote Photoplethysmography (rPPG)
# ─────────────────────────────────────────────────────────────────────────

class RPPGAnalyzer:
    """Extract and verify pulse signal from face video via green-channel analysis."""

    def __init__(self, buffer_seconds: int = 15, fps: float = 15.0):
        self.fps = fps
        self.max_frames = int(buffer_seconds * fps)
        self.green_signal: deque[float] = deque(maxlen=self.max_frames)

    def add_frame(self, image: np.ndarray, landmarks: list[list[float]] | None = None) -> None:
        """Add a frame and extract the mean green-channel value from the forehead region."""
        if image.ndim != 3:
            return

        h, w = image.shape[:2]

        # Use forehead region for rPPG (least movement, good vascular coverage)
        if landmarks and len(landmarks) > 100:
            pts = np.array(landmarks, dtype=np.float32)
            forehead_indices = [10, 67, 109, 338, 297, 21, 54, 103]
            valid = [i for i in forehead_indices if i < len(pts)]
            if valid:
                fp = pts[valid]
                xs = (fp[:, 0] * w).astype(int).clip(0, w - 1)
                ys = (fp[:, 1] * h).astype(int).clip(0, h - 1)
                x_min, x_max = max(xs.min(), 0), min(xs.max(), w)
                y_min, y_max = max(ys.min(), 0), min(ys.max(), h)
                if x_max > x_min and y_max > y_min:
                    roi = image[y_min:y_max, x_min:x_max, 1]  # green channel
                    self.green_signal.append(float(roi.mean()))
                    return

        # Fallback: use upper face region
        roi = image[h // 8:h // 4, w // 4:3 * w // 4, 1]
        self.green_signal.append(float(roi.mean()))

    def analyze(self) -> dict[str, Any]:
        """Analyse the accumulated green-channel signal for pulse."""
        if len(self.green_signal) < 60:  # Need at least ~4 seconds of data
            return {"rppg_available": False, "rppg_score": 0.5}

        signal = np.array(self.green_signal, dtype=np.float64)

        # Detrend (remove slow drift)
        x = np.arange(len(signal))
        poly = np.polyfit(x, signal, 2)
        trend = np.polyval(poly, x)
        detrended = signal - trend

        # Bandpass filter: keep 0.7-4.0 Hz (42-240 BPM)
        freqs = np.fft.rfftfreq(len(detrended), d=1.0 / self.fps)
        fft = np.fft.rfft(detrended)
        mask = (freqs >= 0.7) & (freqs <= 4.0)
        filtered_fft = fft.copy()
        filtered_fft[~mask] = 0
        filtered = np.fft.irfft(filtered_fft, n=len(detrended))

        # Find dominant frequency
        power = np.abs(fft[mask]) ** 2
        if power.size == 0:
            return {"rppg_available": True, "rppg_score": 0.3, "pulse_detected": False}

        peak_idx = np.argmax(power)
        peak_freq = float(freqs[mask][peak_idx])
        estimated_bpm = peak_freq * 60

        # Signal quality: ratio of peak power to total band power
        snr = float(power[peak_idx] / (power.mean() + 1e-8))

        # Pulse is physiologically plausible?
        plausible = 42 <= estimated_bpm <= 180
        clear_signal = snr > 3.0

        if plausible and clear_signal:
            score = min(0.5 + snr * 0.05, 1.0)
        elif plausible:
            score = 0.5
        else:
            score = max(0.0, 0.4 - (snr * 0.02))

        return {
            "rppg_available": True,
            "rppg_score": round(score, 4),
            "pulse_detected": plausible and clear_signal,
            "estimated_bpm": round(estimated_bpm, 1),
            "signal_snr": round(snr, 2),
        }

    def reset(self) -> None:
        self.green_signal.clear()


# ─────────────────────────────────────────────────────────────────────────
# Combined deepfake analysis
# ─────────────────────────────────────────────────────────────────────────

def analyze_deepfake_risk(
    image: np.ndarray | None,
    landmarks: list[list[float]] | None = None,
    client_metrics: dict[str, Any] | None = None,
    temporal_scores: dict[str, float] | None = None,
    rppg_scores: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the full deepfake detection pipeline.

    Returns a dict with:
    - deepfake_score: aggregate 0-1 realness score (1 = real)
    - sub-scores from each detection method
    - anomalies list
    """
    metrics = client_metrics or {}
    anomalies: list[str] = []

    if image is None:
        return {
            "deepfake_score": 0.65,
            "anomalies": ["Frame analysis unavailable – deepfake score is provisional"],
        }

    # Method 1: Frequency domain
    freq = frequency_domain_analysis(image)

    # Method 2: Face boundary
    boundary = face_boundary_analysis(image, landmarks)

    # Method 4: Eye reflections
    eye = eye_reflection_analysis(image, landmarks)

    # Method 5: Mouth interior
    mar = float(metrics.get("mar", 0.0))
    mouth = mouth_interior_analysis(image, landmarks, mar)

    # Weighted aggregate (methods 3 and 6 are stateful, added when available)
    weights = {
        "frequency": 0.30,
        "boundary": 0.25,
        "eye_reflection": 0.15,
        "mouth_interior": 0.10,
        "temporal": 0.10,
        "rppg": 0.10,
    }

    score_components = {
        "frequency": freq["frequency_score"],
        "boundary": boundary["boundary_score"],
        "eye_reflection": eye["eye_reflection_score"],
        "mouth_interior": mouth["mouth_interior_score"],
    }

    # Add temporal scores if available
    if temporal_scores:
        temporal_avg = np.mean(list(temporal_scores.values())) if temporal_scores else 0.5
        score_components["temporal"] = float(temporal_avg)
    else:
        score_components["temporal"] = 0.5

    # Add rPPG scores if available
    if rppg_scores and rppg_scores.get("rppg_available"):
        score_components["rppg"] = rppg_scores["rppg_score"]
    else:
        score_components["rppg"] = 0.5

    deepfake_score = sum(
        score_components.get(k, 0.5) * w for k, w in weights.items()
    )
    deepfake_score = max(0.0, min(deepfake_score, 1.0))

    # Anomaly detection
    if freq["frequency_score"] < 0.4:
        anomalies.append("Frequency spectrum suggests synthetic generation")
    if freq["hfer"] < 0.15:
        anomalies.append("Very low high-frequency energy – possible GAN artefact")
    if boundary["boundary_score"] < 0.4:
        anomalies.append("Face boundary shows possible blending artefacts")
    if eye["eye_reflection_score"] < 0.3:
        anomalies.append("Inconsistent corneal reflections between eyes")
    if temporal_scores and temporal_scores.get("landmark_jitter_score", 1.0) < 0.3:
        anomalies.append("Unnatural facial landmark jitter pattern")
    if rppg_scores and rppg_scores.get("rppg_available") and not rppg_scores.get("pulse_detected"):
        anomalies.append("No physiological pulse signal detected")

    return {
        "deepfake_score": round(deepfake_score, 4),
        "anomalies": anomalies,
        "frequency_analysis": freq,
        "boundary_analysis": boundary,
        "eye_reflection": eye,
        "mouth_interior": mouth,
        "temporal": temporal_scores or {},
        "rppg": rppg_scores or {},
    }
