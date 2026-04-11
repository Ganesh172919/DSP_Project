"""
models/anti_injection.py — LAYER 0: Anti-Injection Guard

Runs BEFORE any face processing to detect virtual/fake camera sources.

Detection strategy:
  1. Enumerate OS camera devices, flag known virtual driver names
  2. Inject 3 random single-pixel noise frames; measure PRNU variance
     (real sensors exhibit Photo Response Non-Uniformity; virtual cams don't)
  3. Check frame metadata heuristics: focal length, lens distortion, rolling shutter

Output: InjectionResult(is_real_camera, confidence, flags)
"""

import platform
import re
import subprocess
import logging
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from app.config import VIRTUAL_CAMERA_SIGNATURES, PRNU_VARIANCE_THRESHOLD

logger = logging.getLogger(__name__)


@dataclass
class InjectionResult:
    is_real_camera: bool
    confidence: float
    flags: list[str] = field(default_factory=list)


class AntiInjectionGuard:
    """
    Layer 0 — validates that the video source is a real physical camera.
    """

    def __init__(self):
        self.known_virtual_names = [v.lower() for v in VIRTUAL_CAMERA_SIGNATURES]

    # ─── 1. Enumerate cameras and flag virtual drivers ───────────────────

    def enumerate_cameras(self) -> list[dict]:
        """
        Query OS for connected camera devices.
        Returns list of {index, name, is_virtual} dicts.
        """
        cameras = []
        system = platform.system()

        if system == "Windows":
            cameras = self._enumerate_windows()
        elif system == "Linux":
            cameras = self._enumerate_linux()
        elif system == "Darwin":
            cameras = self._enumerate_macos()
        else:
            logger.warning(f"Unsupported OS for camera enumeration: {system}")
            # Fallback: probe first 5 indices
            for idx in range(5):
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    cameras.append({"index": idx, "name": f"Camera {idx}", "is_virtual": False})
                    cap.release()

        # Flag virtual cameras
        for cam in cameras:
            name_lower = cam["name"].lower()
            cam["is_virtual"] = any(sig in name_lower for sig in self.known_virtual_names)

        return cameras

    def _enumerate_windows(self) -> list[dict]:
        """Use WMI via PowerShell to list video capture devices."""
        cameras = []
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'Camera' -or $_.PNPClass -eq 'Image' } | Select-Object -ExpandProperty Name"],
                capture_output=True, text=True, timeout=5
            )
            for idx, line in enumerate(result.stdout.strip().split("\n")):
                name = line.strip()
                if name:
                    cameras.append({"index": idx, "name": name, "is_virtual": False})
        except Exception as e:
            logger.warning(f"Windows camera enumeration failed: {e}")
            # Fallback
            for idx in range(5):
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    cameras.append({"index": idx, "name": f"Camera {idx}", "is_virtual": False})
                    cap.release()
        return cameras

    def _enumerate_linux(self) -> list[dict]:
        """Read /sys/class/video4linux/ for device names."""
        cameras = []
        try:
            import glob
            devices = sorted(glob.glob("/sys/class/video4linux/video*"))
            for dev in devices:
                idx = int(dev.split("video")[-1])
                try:
                    name = open(f"{dev}/name").read().strip()
                except FileNotFoundError:
                    name = f"video{idx}"
                cameras.append({"index": idx, "name": name, "is_virtual": False})
        except Exception as e:
            logger.warning(f"Linux camera enumeration failed: {e}")
        return cameras

    def _enumerate_macos(self) -> list[dict]:
        """Use system_profiler to list cameras on macOS."""
        cameras = []
        try:
            result = subprocess.run(
                ["system_profiler", "SPCameraDataType"],
                capture_output=True, text=True, timeout=5
            )
            for idx, match in enumerate(re.findall(r"^\s{4}(\S.+):$", result.stdout, re.MULTILINE)):
                cameras.append({"index": idx, "name": match.strip(), "is_virtual": False})
        except Exception as e:
            logger.warning(f"macOS camera enumeration failed: {e}")
        return cameras

    # ─── 2. PRNU noise analysis ──────────────────────────────────────────

    def check_prnu(self, cap: cv2.VideoCapture, num_frames: int = 3) -> tuple[float, bool]:
        """
        Inject 3 black-frame reads and measure sensor noise variance.
        Real cameras exhibit PRNU (Photo Response Non-Uniformity) — each pixel
        has a slightly different response. Virtual cameras produce uniform output.

        Returns: (variance, is_real)
        """
        noise_samples = []

        for _ in range(num_frames):
            ret, frame = cap.read()
            if not ret:
                continue
            # Convert to grayscale float
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float64)
            noise_samples.append(gray)

        if len(noise_samples) < 2:
            return 0.0, False

        # Compute pixel-wise variance across frames
        stacked = np.stack(noise_samples, axis=0)
        pixel_variance = np.var(stacked, axis=0)
        mean_variance = float(np.mean(pixel_variance))

        # Real sensors: mean_variance > threshold (thermal + shot noise)
        is_real = mean_variance > PRNU_VARIANCE_THRESHOLD
        return mean_variance, is_real

    # ─── 3. Frame metadata heuristics ────────────────────────────────────

    def check_frame_metadata(self, cap: cv2.VideoCapture) -> tuple[float, list[str]]:
        """
        Analyze frame properties for signs of virtual camera injection.
        Returns: (suspicion_score, flags)
        """
        flags = []
        score = 0.0

        # Check resolution — virtual cams often use non-standard resolutions
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Standard webcam resolutions
        standard_resolutions = [
            (640, 480), (1280, 720), (1920, 1080), (320, 240), (800, 600),
            (1280, 960), (1600, 1200), (2560, 1440), (3840, 2160),
        ]
        if (width, height) not in standard_resolutions:
            flags.append(f"non_standard_resolution:{width}x{height}")
            score += 0.2

        # Exact 30.0 or 60.0 FPS is suspicious (real cameras: 29.97, 59.94)
        if fps in (30.0, 60.0, 25.0):
            flags.append(f"exact_fps:{fps}")
            score += 0.15

        # Read a frame and check for lens distortion (barrel/pincushion)
        ret, frame = cap.read()
        if ret:
            # Real cameras have non-zero lens distortion at edges
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)

            # Check edge density in corners vs center
            h, w = edges.shape
            corner_size = h // 4
            center_crop = edges[h//4:3*h//4, w//4:3*w//4]
            corners = np.concatenate([
                edges[:corner_size, :corner_size].ravel(),
                edges[:corner_size, -corner_size:].ravel(),
                edges[-corner_size:, :corner_size].ravel(),
                edges[-corner_size:, -corner_size:].ravel(),
            ])

            center_density = np.mean(center_crop > 0)
            corner_density = np.mean(corners > 0) if len(corners) > 0 else 0

            # Virtual cams: uniform sharpness; real: slight corner softening
            if corner_density > 0 and abs(center_density - corner_density) < 0.01:
                flags.append("uniform_sharpness_no_lens_distortion")
                score += 0.15

            # Check for rolling shutter artifacts (horizontal banding)
            row_means = np.mean(gray.astype(np.float64), axis=1)
            row_diff = np.diff(row_means)
            rolling_shutter_indicator = float(np.std(row_diff))
            if rolling_shutter_indicator < 0.5:
                flags.append("no_rolling_shutter_artifacts")
                score += 0.1

        return min(score, 1.0), flags

    # ─── Main validation ─────────────────────────────────────────────────

    def validate(self, cap: Optional[cv2.VideoCapture] = None, camera_index: int = 0) -> InjectionResult:
        """
        Run all anti-injection checks on the given camera.

        Args:
            cap: existing VideoCapture object (optional)
            camera_index: camera index to open if cap not provided

        Returns: InjectionResult
        """
        flags = []
        scores = []
        own_cap = False

        # Open camera if not provided
        if cap is None:
            cap = cv2.VideoCapture(camera_index)
            own_cap = True

        if not cap.isOpened():
            return InjectionResult(is_real_camera=False, confidence=0.0, flags=["camera_not_accessible"])

        try:
            # Check 1: Device name
            cameras = self.enumerate_cameras()
            virtual_found = [c for c in cameras if c.get("is_virtual", False)]
            if virtual_found:
                flags.append(f"virtual_camera_detected:{virtual_found[0]['name']}")
                scores.append(0.0)
            else:
                scores.append(1.0)

            # Check 2: PRNU noise analysis
            prnu_variance, prnu_real = self.check_prnu(cap)
            if not prnu_real:
                flags.append(f"low_prnu_variance:{prnu_variance:.4f}")
                scores.append(0.2)
            else:
                scores.append(1.0)

            # Check 3: Frame metadata heuristics
            suspicion, meta_flags = self.check_frame_metadata(cap)
            flags.extend(meta_flags)
            scores.append(1.0 - suspicion)

            # Aggregate
            confidence = float(np.mean(scores))
            is_real = confidence >= 0.6 and not virtual_found

            return InjectionResult(
                is_real_camera=is_real,
                confidence=round(confidence, 4),
                flags=flags,
            )

        finally:
            if own_cap:
                cap.release()


# ═══════════════════════════════════════════════════════════════════════════
# Standalone DEMO — run this file directly
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json

    guard = AntiInjectionGuard()

    print("=== Camera Enumeration ===")
    cameras = guard.enumerate_cameras()
    for c in cameras:
        print(f"  [{c['index']}] {c['name']}  virtual={c['is_virtual']}")

    print("\n=== Anti-Injection Validation ===")
    result = guard.validate(camera_index=0)
    print(json.dumps({
        "is_real_camera": result.is_real_camera,
        "confidence": result.confidence,
        "flags": result.flags,
    }, indent=2))
