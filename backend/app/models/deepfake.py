"""
models/deepfake.py — LAYER 4: Deepfake Detection

Hybrid CNN + Training-Free approach (Approach B):

A) Spectral FFT Analysis — detects GAN upsampling artifacts
B) CNN Feature Extractor — EfficientNet-B0 ImageNet features for anomaly detection
C) Face Boundary Artifacts — gradient discontinuity at face edges
D) Eye Reflection Consistency — specular highlight comparison
E) Skin Texture Uniformity — high-frequency variance analysis
F) Color Channel Correlation — cross-channel correlation anomalies
G) Temporal Flicker — frame-to-frame face region stability

FUSION: Weighted combination → final deepfake_score
  deepfake_score < 0.30 → real face (low deepfake probability)
  deepfake_score > 0.30 → likely deepfake
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from app.config import (
    SPECTRAL_BANDS, DEEPFAKE_SPECTRAL_WEIGHT, DEEPFAKE_CNN_WEIGHT,
    DEEPFAKE_FLAG_THRESHOLD, DEVICE,
    BOUNDARY_ARTIFACT_THRESHOLD, EYE_REFLECTION_THRESHOLD,
    SKIN_UNIFORMITY_THRESHOLD, COLOR_CORRELATION_THRESHOLD,
    TEMPORAL_FLICKER_THRESHOLD,
)

logger = logging.getLogger(__name__)


@dataclass
class DeepfakeScores:
    spectral_score: float = 0.0         # 0 = real, 1 = deepfake
    cnn_feature_score: float = 0.0
    boundary_score: float = 0.0
    eye_reflection_score: float = 0.0
    skin_uniformity_score: float = 0.0
    color_correlation_score: float = 0.0
    temporal_flicker_score: float = 0.0

@dataclass
class DeepfakeResult:
    is_deepfake: bool
    deepfake_probability: float  # 0 = certainly real, 1 = certainly deepfake
    scores: DeepfakeScores = field(default_factory=DeepfakeScores)
    flags: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# A) Spectral FFT Analysis
# ═══════════════════════════════════════════════════════════════════════════

class SpectralAnalyzer:
    """
    Analyzes frequency-domain patterns that distinguish real from
    GAN-generated/deepfake faces.

    GAN artifacts:
    - Upsampling leaves periodic patterns in high-frequency domain
    - Checkerboard artifacts from transposed convolutions
    - Unusual spectral decay patterns
    """

    def __init__(self, num_bands: int = SPECTRAL_BANDS):
        self.num_bands = num_bands

    def extract_spectral_features(self, face_crop: np.ndarray) -> np.ndarray:
        """Extract azimuthally-averaged power spectrum features."""
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY).astype(np.float64)
        gray = cv2.resize(gray, (128, 128))

        # Apply Hanning window
        h, w = gray.shape
        window = np.outer(np.hanning(h), np.hanning(w))
        gray = gray * window

        # FFT
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)

        # Remove DC
        cy, cx = h // 2, w // 2
        magnitude[cy, cx] = 0

        # Azimuthal averaging in frequency bands
        max_r = min(cy, cx)
        y, x = np.ogrid[:h, :w]
        radius = np.sqrt((x - cx)**2 + (y - cy)**2)

        bands = np.linspace(0, max_r, self.num_bands + 1)
        features = []
        for i in range(self.num_bands):
            mask = (radius >= bands[i]) & (radius < bands[i+1])
            if np.any(mask):
                features.append(float(np.mean(np.log1p(magnitude[mask]))))
            else:
                features.append(0.0)

        return np.array(features, dtype=np.float32)

    def compute_spectral_score(self, face_crop: np.ndarray) -> float:
        """
        Compute deepfake probability from spectral features.

        Real faces: smooth spectral decay (natural 1/f falloff)
        GAN faces: irregular peaks, spectral bumps from upsampling

        Returns: 0 = likely real, 1 = likely deepfake
        """
        features = self.extract_spectral_features(face_crop)

        if len(features) < 3:
            return 0.5

        # 1. Spectral decay smoothness
        # Real: monotonically decreasing power spectrum
        # Fake: non-monotonic bumps
        diffs = np.diff(features)
        non_monotonic = np.sum(diffs > 0) / max(len(diffs), 1)

        # 2. High-frequency energy ratio
        # GAN: elevated high-freq energy from upsampling artifacts
        mid = len(features) // 2
        lf_energy = np.sum(features[:mid])
        hf_energy = np.sum(features[mid:])
        hf_ratio = hf_energy / (lf_energy + 1e-8)

        # 3. Spectral roughness
        # GAN: rougher spectrum due to artifacts
        roughness = float(np.std(np.diff(features)))

        # Combine into deepfake score
        score = 0.0
        score += 0.4 * non_monotonic  # non-monotonic decay → deepfake
        score += 0.3 * min(hf_ratio / 0.3, 1.0)  # high HF ratio → deepfake
        score += 0.3 * min(roughness / 0.5, 1.0)  # rough spectrum → deepfake

        return float(np.clip(score, 0.0, 1.0))


# ═══════════════════════════════════════════════════════════════════════════
# B) CNN Feature Extractor — EfficientNet-B0 (ImageNet)
# ═══════════════════════════════════════════════════════════════════════════

class DeepfakeCNN:
    """
    Approach B CNN: EfficientNet-B0 with ImageNet pretrained weights.

    Without fine-tuning, analyzes deep feature distributions for anomalies.
    With fine-tuned weights (if available), provides direct deepfake prediction.
    """

    def __init__(self):
        self.model = None
        self.feature_extractor = None
        self.transform = None
        self._initialized = False
        self._has_finetuned = False

    def _lazy_init(self):
        if self._initialized:
            return

        import torch
        import torch.nn as nn
        from torchvision import transforms
        from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights

        self.device = torch.device(DEVICE)

        # Load pretrained EfficientNet-B0
        full_model = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)

        # Check for fine-tuned weights
        weight_path = os.path.join("weights", "deepfake_efficientnet.pth")
        if os.path.exists(weight_path):
            full_model.classifier = nn.Sequential(
                nn.Dropout(p=0.3),
                nn.Linear(1280, 1),
                nn.Sigmoid(),
            )
            state_dict = torch.load(weight_path, map_location=self.device)
            full_model.load_state_dict(state_dict)
            self._has_finetuned = True
            self.model = full_model.to(self.device)
            self.model.eval()
            logger.info("Loaded fine-tuned deepfake EfficientNet weights")
        else:
            # Use as feature extractor
            self.feature_extractor = full_model.features
            self.feature_extractor = self.feature_extractor.to(self.device)
            self.feature_extractor.eval()
            logger.info("Deepfake CNN: using ImageNet EfficientNet-B0 as feature extractor")

        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((112, 112)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

        self._initialized = True

    def predict(self, aligned_face: np.ndarray) -> float:
        """
        Predict deepfake probability.
        Returns: 0 = real, 1 = deepfake
        """
        self._lazy_init()
        import torch

        rgb = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
        tensor = self.transform(rgb).unsqueeze(0).to(self.device)

        with torch.no_grad():
            if self._has_finetuned and self.model is not None:
                return float(self.model(tensor).item())
            else:
                features = self.feature_extractor(tensor)
                return self._analyze_features(features)

    def _analyze_features(self, features) -> float:
        """
        Analyze deep features for deepfake anomalies.

        Deepfakes tend to have:
        - More spatially uniform feature activations (less texture detail)
        - Abnormal channel activation patterns
        - Smoother feature gradients (less detail in invisible artifacts)
        """
        import torch

        feat = features.squeeze(0)  # [C, H, W]

        # Feature 1: Spatial uniformity
        # Deepfakes: more uniform features (smooth skin, less pores)
        spatial_var = torch.var(feat, dim=[1, 2])
        mean_spatial_var = float(spatial_var.mean().item())

        # Feature 2: Channel activation entropy
        # Real: diverse channel activations; Fake: more correlated
        channel_means = feat.mean(dim=[1, 2])
        channel_std = float(channel_means.std().item())

        # Feature 3: Feature gradient smoothness
        # Deepfakes: smoother gradients in feature space
        dx = torch.abs(feat[:, :, 1:] - feat[:, :, :-1])
        dy = torch.abs(feat[:, 1:, :] - feat[:, :-1, :])
        gradient_mean = float((dx.mean() + dy.mean()).item() / 2)

        # Lower values = smoother = more likely deepfake
        score = 0.0
        # Low spatial variance → deepfake
        score += 0.35 * max(0, 1.0 - mean_spatial_var / 0.05)
        # Low channel diversity → deepfake
        score += 0.35 * max(0, 1.0 - channel_std / 0.15)
        # Low gradient → deepfake (too smooth)
        score += 0.30 * max(0, 1.0 - gradient_mean / 0.02)

        return float(np.clip(score, 0.0, 1.0))


# ═══════════════════════════════════════════════════════════════════════════
# C) Training-Free Deepfake Checks
# ═══════════════════════════════════════════════════════════════════════════

class DeepfakeAnalyzer:
    """
    Training-free deepfake detection checks.
    All work with pure OpenCV/numpy — no models needed.
    """

    @staticmethod
    def check_boundary_artifacts(face_crop: np.ndarray) -> float:
        """
        Detect face-swap blending artifacts at face boundary.

        Face swaps often show gradient discontinuity at blend boundaries.
        Returns: 0 = natural (real), 1 = artifacts found (deepfake)
        """
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY).astype(np.float64)
        h, w = gray.shape

        # Create face-shaped mask (elliptical)
        mask = np.zeros_like(gray, dtype=np.uint8)
        center = (w // 2, h // 2)
        axes = (int(w * 0.4), int(h * 0.45))
        cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)

        # Compute Laplacian at boundary
        dilated = cv2.dilate(mask, np.ones((7, 7), np.uint8))
        eroded = cv2.erode(mask, np.ones((7, 7), np.uint8))
        boundary = dilated - eroded

        laplacian = np.abs(cv2.Laplacian(gray, cv2.CV_64F))
        boundary_laplacian = laplacian[boundary > 0]
        interior_laplacian = laplacian[eroded > 0]

        if len(boundary_laplacian) == 0 or len(interior_laplacian) == 0:
            return 0.0

        boundary_mean = float(np.mean(boundary_laplacian))
        interior_mean = float(np.mean(interior_laplacian))

        # High boundary-to-interior gradient ratio → blending artifact
        ratio = boundary_mean / (interior_mean + 1e-8)

        if ratio > 2.0:
            return min((ratio - 1.0) / 3.0, 1.0)
        return 0.0

    @staticmethod
    def check_eye_reflection(face_crop: np.ndarray) -> float:
        """
        Compare specular highlights in left/right eyes.

        Real eyes have consistent specular reflections from the same light source.
        Deepfakes often have inconsistent or missing reflections.

        Returns: 0 = consistent (real), 1 = inconsistent (deepfake)
        """
        h, w = face_crop.shape[:2]

        # Extract eye regions (approximate positions in aligned face)
        eye_h = h // 4
        eye_w = w // 4
        left_eye_region = face_crop[h//5:h//5+eye_h, w//6:w//6+eye_w]
        right_eye_region = face_crop[h//5:h//5+eye_h, w-w//6-eye_w:w-w//6]

        if left_eye_region.size == 0 or right_eye_region.size == 0:
            return 0.0

        # Find brightest spots (specular highlights)
        left_gray = cv2.cvtColor(left_eye_region, cv2.COLOR_BGR2GRAY)
        right_gray = cv2.cvtColor(right_eye_region, cv2.COLOR_BGR2GRAY)

        left_max = float(np.max(left_gray))
        right_max = float(np.max(right_gray))
        left_mean = float(np.mean(left_gray))
        right_mean = float(np.mean(right_gray))

        # Check for specular highlight presence
        left_has_spec = (left_max - left_mean) > 30
        right_has_spec = (right_max - right_mean) > 30

        if not left_has_spec and not right_has_spec:
            return 0.3  # no reflections — somewhat suspicious

        if left_has_spec != right_has_spec:
            return 0.7  # only one eye has reflection — suspicious

        # Compare reflection positions
        left_peak_pos = np.unravel_index(np.argmax(left_gray), left_gray.shape)
        right_peak_pos = np.unravel_index(np.argmax(right_gray), right_gray.shape)

        # Normalize positions
        left_norm = np.array(left_peak_pos) / np.array(left_gray.shape)
        right_norm = np.array(right_peak_pos) / np.array(right_gray.shape)

        pos_diff = np.linalg.norm(left_norm - right_norm)

        # Small difference = consistent = real
        if pos_diff > 0.5:
            return 0.6
        return max(0.0, pos_diff / 0.5 * 0.4)

    @staticmethod
    def check_skin_uniformity(face_crop: np.ndarray) -> float:
        """
        Analyze skin texture uniformity across face zones.

        Deepfakes often have unnaturally uniform skin texture
        without natural pores, wrinkles, and micro-blemishes.

        Returns: 0 = natural variation (real), 1 = too uniform (deepfake)
        """
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY).astype(np.float64)
        h, w = gray.shape

        # Divide face into zones
        zones = [
            gray[:h//3, :w//3],           # forehead left
            gray[:h//3, w//3:2*w//3],     # forehead center
            gray[:h//3, 2*w//3:],         # forehead right
            gray[h//3:2*h//3, :w//3],     # midface left
            gray[h//3:2*h//3, 2*w//3:],   # midface right
            gray[2*h//3:, :w//3],         # lower left
            gray[2*h//3:, w//3:2*w//3],   # lower center
            gray[2*h//3:, 2*w//3:],       # lower right
        ]

        # Compute high-frequency content per zone
        hf_values = []
        for zone in zones:
            if zone.size < 10:
                continue
            laplacian = cv2.Laplacian(zone.astype(np.uint8), cv2.CV_64F)
            hf_values.append(float(np.var(laplacian)))

        if len(hf_values) < 4:
            return 0.5

        # Natural faces: high diversity in HF content across zones
        # Deepfakes: more uniform HF content
        hf_std = float(np.std(hf_values))
        hf_mean = float(np.mean(hf_values))
        cv = hf_std / (hf_mean + 1e-8)  # coefficient of variation

        # Low CV = too uniform → deepfake
        if cv < 0.3:
            return 0.7
        elif cv < 0.5:
            return 0.3
        return 0.1  # high variation = natural

    @staticmethod
    def check_color_correlation(face_crop: np.ndarray) -> float:
        """
        Analyze cross-channel color correlation.

        GAN-generated faces often have abnormal correlations
        between R, G, B channels compared to natural images.

        Returns: 0 = normal correlation (real), 1 = abnormal (deepfake)
        """
        b, g, r = cv2.split(face_crop)
        b, g, r = b.astype(np.float64).ravel(), g.astype(np.float64).ravel(), r.astype(np.float64).ravel()

        # Compute channel correlations
        rg_corr = float(np.corrcoef(r, g)[0, 1])
        rb_corr = float(np.corrcoef(r, b)[0, 1])
        gb_corr = float(np.corrcoef(g, b)[0, 1])

        # Natural images: R-G highly correlated (~0.90-0.99)
        # GAN images: often have slightly lower or higher correlations

        # Check for abnormal correlation patterns
        corrs = [rg_corr, rb_corr, gb_corr]
        mean_corr = np.mean(corrs)
        std_corr = np.std(corrs)

        # Very high uniform correlation (> 0.99) or unusual patterns
        score = 0.0
        if mean_corr > 0.995:
            score += 0.4  # unnaturally high correlation
        if std_corr < 0.02:
            score += 0.3  # unnaturally low variance between channels
        if any(c < 0.7 for c in corrs):
            score += 0.3  # unusually low correlation for face

        return float(np.clip(score, 0.0, 1.0))

    @staticmethod
    def check_temporal_flicker(frames: list[np.ndarray]) -> float:
        """
        Detect temporal flicker in the face region across frames.

        Real-time deepfakes often exhibit micro-flickering
        due to frame-by-frame generation inconsistencies.

        Returns: 0 = stable (real), 1 = flickering (deepfake)
        """
        if len(frames) < 5:
            return 0.0  # not enough data

        # Extract face region intensity from each frame
        intensities = []
        for frame in frames[::2]:
            h, w = frame.shape[:2]
            # Center face region
            cx, cy = w // 2, h // 2
            rh, rw = h // 3, w // 3
            roi = frame[max(0,cy-rh):cy+rh, max(0,cx-rw):cx+rw]
            if roi.size > 0:
                intensities.append(float(np.mean(roi)))

        if len(intensities) < 5:
            return 0.0

        # Compute temporal variance
        diffs = np.diff(intensities)
        temporal_var = float(np.var(diffs))
        mean_abs_diff = float(np.mean(np.abs(diffs)))

        # High-frequency oscillation detection
        sign_changes = sum(1 for i in range(1, len(diffs))
                          if diffs[i] * diffs[i-1] < 0)
        oscillation_ratio = sign_changes / max(len(diffs) - 1, 1)

        # Deepfake flicker: high oscillation with low magnitude
        if oscillation_ratio > 0.7 and mean_abs_diff > 0.5:
            return min(oscillation_ratio * (mean_abs_diff / 3.0), 1.0)

        return 0.0


# ═══════════════════════════════════════════════════════════════════════════
# FUSION
# ═══════════════════════════════════════════════════════════════════════════

class DeepfakeFusion:
    """Fuses all deepfake signals into a single probability score."""

    def __init__(self):
        # Approach B weights — emphasize CNN + spectral
        self.w_spectral = 0.25
        self.w_cnn = 0.25
        self.w_boundary = 0.15
        self.w_eye = 0.10
        self.w_skin = 0.10
        self.w_color = 0.10
        self.w_temporal = 0.05

    def fuse(self, scores: DeepfakeScores, has_video: bool = False) -> float:
        """Weighted fusion. Redistributes temporal weight if no video."""
        w_t = self.w_temporal if has_video else 0.0
        total = (self.w_spectral + self.w_cnn + self.w_boundary +
                 self.w_eye + self.w_skin + self.w_color + w_t)

        if total == 0:
            return 0.0

        fused = (
            self.w_spectral * scores.spectral_score +
            self.w_cnn * scores.cnn_feature_score +
            self.w_boundary * scores.boundary_score +
            self.w_eye * scores.eye_reflection_score +
            self.w_skin * scores.skin_uniformity_score +
            self.w_color * scores.color_correlation_score +
            w_t * scores.temporal_flicker_score
        ) / total

        return round(float(np.clip(fused, 0.0, 1.0)), 4)


# ═══════════════════════════════════════════════════════════════════════════
# Main orchestrator
# ═══════════════════════════════════════════════════════════════════════════

class DeepfakeDetector:
    """
    Layer 4 — Full deepfake detection with Approach B (Hybrid CNN + Training-Free).
    """

    def __init__(self):
        self.spectral = SpectralAnalyzer()
        self.cnn = DeepfakeCNN()
        self.analyzer = DeepfakeAnalyzer()
        self.fusion = DeepfakeFusion()

    def detect(
        self,
        aligned_face: np.ndarray,
        frames: Optional[list[np.ndarray]] = None,
    ) -> DeepfakeResult:
        """
        Full deepfake detection.

        Args:
            aligned_face: 112×112 aligned face crop
            frames: list of raw video frames for temporal analysis

        Returns: DeepfakeResult with probability and detailed scores
        """
        has_video = frames is not None and len(frames) > 5

        scores = DeepfakeScores()
        flags = []

        # A) Spectral FFT
        scores.spectral_score = self.spectral.compute_spectral_score(aligned_face)
        if scores.spectral_score > DEEPFAKE_FLAG_THRESHOLD:
            flags.append(f"spectral_anomaly:{scores.spectral_score:.3f}")

        # B) CNN features
        scores.cnn_feature_score = self.cnn.predict(aligned_face)
        if scores.cnn_feature_score > DEEPFAKE_FLAG_THRESHOLD:
            flags.append(f"cnn_anomaly:{scores.cnn_feature_score:.3f}")

        # C) Boundary artifacts
        scores.boundary_score = self.analyzer.check_boundary_artifacts(aligned_face)
        if scores.boundary_score > BOUNDARY_ARTIFACT_THRESHOLD:
            flags.append(f"boundary_artifact:{scores.boundary_score:.3f}")

        # D) Eye reflection
        scores.eye_reflection_score = self.analyzer.check_eye_reflection(aligned_face)
        if scores.eye_reflection_score > EYE_REFLECTION_THRESHOLD:
            flags.append(f"eye_reflection_mismatch:{scores.eye_reflection_score:.3f}")

        # E) Skin uniformity
        scores.skin_uniformity_score = self.analyzer.check_skin_uniformity(aligned_face)
        if scores.skin_uniformity_score > SKIN_UNIFORMITY_THRESHOLD:
            flags.append(f"skin_too_uniform:{scores.skin_uniformity_score:.3f}")

        # F) Color correlation
        scores.color_correlation_score = self.analyzer.check_color_correlation(aligned_face)
        if scores.color_correlation_score > COLOR_CORRELATION_THRESHOLD:
            flags.append(f"color_correlation_anomaly:{scores.color_correlation_score:.3f}")

        # G) Temporal flicker (video only)
        if has_video:
            scores.temporal_flicker_score = self.analyzer.check_temporal_flicker(frames)
            if scores.temporal_flicker_score > TEMPORAL_FLICKER_THRESHOLD:
                flags.append(f"temporal_flicker:{scores.temporal_flicker_score:.3f}")

        # Fusion
        probability = self.fusion.fuse(scores, has_video=has_video)
        is_deepfake = probability > DEEPFAKE_FLAG_THRESHOLD

        return DeepfakeResult(
            is_deepfake=is_deepfake,
            deepfake_probability=probability,
            scores=scores,
            flags=flags,
        )
