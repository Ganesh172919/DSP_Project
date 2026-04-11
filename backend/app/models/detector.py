"""
models/detector.py — LAYER 1: Face Detection & Alignment

Uses OpenCV's built-in FaceDetectorYN (YuNet model) — a lightweight ONNX
face detector that ships with OpenCV 4.5.4+.

Benefits over insightface/mediapipe:
  - No C++ compilation required
  - No heavy downloads (model is ~337 KB)
  - Gives bounding box + 5 facial landmarks natively
  - Fast CPU inference

Output per detection:
  - bounding box [x1, y1, x2, y2]
  - 5 facial landmarks (eye centers, nose tip, mouth corners)
  - confidence score
  - aligned 112×112 face crop
"""

import logging
import os
import shutil
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from app.config import (
    FACE_CONFIDENCE_THRESHOLD, MIN_FACE_AREA_RATIO,
    MAX_YAW_DEGREES, MAX_PITCH_DEGREES, ALIGNED_FACE_SIZE, MODEL_DIR,
)

logger = logging.getLogger(__name__)


# ─── YuNet model download ───────────────────────────────────────────────
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
YUNET_MODEL_NAME = "face_detection_yunet_2023mar.onnx"


def _download_yunet_model(model_dir: Path) -> Path:
    """Download the YuNet face detection ONNX model (~337 KB)."""
    model_path = model_dir / YUNET_MODEL_NAME
    if model_path.exists():
        return model_path

    model_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading YuNet face detector (~337 KB) ...")

    try:
        urllib.request.urlretrieve(str(YUNET_URL), str(model_path))
        logger.info(f"Downloaded YuNet model to {model_path}")
        return model_path
    except Exception as e:
        logger.error(f"Failed to download YuNet model: {e}")
        raise RuntimeError(
            f"Could not download YuNet model.\n"
            f"Please download manually from:\n  {YUNET_URL}\n"
            f"Save to:\n  {model_path}\n"
            f"Error: {e}"
        )


# ─── Canonical reference landmarks for 112×112 alignment ────────────────
# Standard ArcFace alignment target.
# "left/right" = viewer's perspective (image coords).
REFERENCE_LANDMARKS = np.array([
    [38.2946, 51.6963],   # left eye  (viewer's left  = person's right eye)
    [73.5318, 51.5014],   # right eye (viewer's right = person's left eye)
    [56.0252, 71.7366],   # nose tip
    [41.5493, 92.3655],   # left mouth corner
    [70.7299, 92.2041],   # right mouth corner
], dtype=np.float32)


@dataclass
class FaceDetection:
    bbox: np.ndarray             # [x1, y1, x2, y2]
    landmarks: np.ndarray        # (5, 2) — 5 facial landmarks
    confidence: float
    aligned_face: np.ndarray     # 112×112×3 BGR face crop
    yaw: float = 0.0
    pitch: float = 0.0
    face_area_ratio: float = 0.0


@dataclass
class DetectionResult:
    face_detected: bool
    face_confidence: float = 0.0
    detection: Optional[FaceDetection] = None
    rejection_reason: Optional[str] = None


class FaceDetector:
    """
    Layer 1 — OpenCV YuNet face detection + similarity-transform alignment.
    No compilation, no heavy dependencies.
    """

    def __init__(self):
        self.detector = None
        self._initialized = False
        self._current_size = (0, 0)

    def _lazy_init(self):
        """Download and load YuNet model on first use."""
        if self._initialized:
            return

        model_path = _download_yunet_model(MODEL_DIR)
        self.model_path = str(model_path)

        # Create detector — we'll set input size per-frame in detect()
        self.detector = cv2.FaceDetectorYN.create(
            self.model_path,
            "",                # config (empty for ONNX)
            (320, 320),        # initial input size (will be updated per-frame)
            0.5,               # score threshold
            0.3,               # NMS threshold
            5000,              # top_k
        )
        self._initialized = True
        logger.info("YuNet face detector loaded successfully")

    def _estimate_pose(self, landmarks: np.ndarray) -> tuple[float, float]:
        """
        Estimate yaw and pitch from 5 facial landmarks using geometric heuristics.
        """
        left_eye = landmarks[0]
        right_eye = landmarks[1]
        nose = landmarks[2]
        left_mouth = landmarks[3]
        right_mouth = landmarks[4]

        eye_center = (left_eye + right_eye) / 2.0
        eye_dist = np.linalg.norm(right_eye - left_eye)

        if eye_dist < 1e-6:
            return 0.0, 0.0

        # Yaw: nose offset from eye center
        nose_offset_x = (nose[0] - eye_center[0]) / eye_dist
        yaw = float(np.degrees(np.arctan2(nose_offset_x, 1.0)))

        # Pitch: nose vertical position relative to eyes-mouth range
        mouth_center = (left_mouth + right_mouth) / 2.0
        face_height = mouth_center[1] - eye_center[1]
        if face_height < 1e-6:
            return yaw, 0.0

        nose_relative_y = (nose[1] - eye_center[1]) / face_height
        pitch = float((nose_relative_y - 0.45) * 60.0)

        return yaw, pitch

    def _align_face(self, image: np.ndarray, landmarks: np.ndarray) -> np.ndarray:
        """
        Similarity transform warp → canonical 112×112 crop.
        """
        src_pts = landmarks.astype(np.float32)
        dst_pts = REFERENCE_LANDMARKS.astype(np.float32)

        tform, _ = cv2.estimateAffinePartial2D(src_pts, dst_pts)

        if tform is None:
            # Fallback: simple crop + resize
            x1, y1 = landmarks.min(axis=0).astype(int)
            x2, y2 = landmarks.max(axis=0).astype(int)
            pad = max(x2 - x1, y2 - y1) // 2
            h, w = image.shape[:2]
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            crop = image[
                max(0, cy - pad):min(h, cy + pad),
                max(0, cx - pad):min(w, cx + pad),
            ]
            if crop.size == 0:
                return cv2.resize(image, ALIGNED_FACE_SIZE)
            return cv2.resize(crop, ALIGNED_FACE_SIZE)

        aligned = cv2.warpAffine(
            image, tform, ALIGNED_FACE_SIZE,
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return aligned

    def detect(self, image: np.ndarray) -> DetectionResult:
        """
        Detect the primary (largest/highest-confidence) face in the image.

        YuNet output per detection (15 values):
          [x, y, w, h,
           right_eye_x, right_eye_y,     # person's right = viewer's left
           left_eye_x, left_eye_y,       # person's left  = viewer's right
           nose_x, nose_y,
           right_mouth_x, right_mouth_y, # person's right = viewer's left
           left_mouth_x, left_mouth_y,   # person's left  = viewer's right
           score]
        """
        self._lazy_init()

        h, w = image.shape[:2]

        # Update detector input size if frame dimensions changed
        if (w, h) != self._current_size:
            self.detector.setInputSize((w, h))
            self._current_size = (w, h)

        t0 = time.perf_counter()
        _, faces = self.detector.detect(image)
        dt = (time.perf_counter() - t0) * 1000

        if faces is None or len(faces) == 0:
            logger.debug(f"Detection took {dt:.1f} ms — no faces")
            return DetectionResult(face_detected=False, rejection_reason="no_face_detected")

        logger.debug(f"Detection took {dt:.1f} ms, found {len(faces)} face(s)")

        # Pick highest-confidence face
        best_idx = int(np.argmax(faces[:, -1]))
        face = faces[best_idx]

        confidence = float(face[14])

        # ── Confidence check ─────────────────────────────────────────────
        if confidence < FACE_CONFIDENCE_THRESHOLD:
            return DetectionResult(
                face_detected=True,
                face_confidence=confidence,
                rejection_reason=f"low_confidence:{confidence:.3f}",
            )

        # ── Bounding box ─────────────────────────────────────────────────
        x1 = max(0, int(face[0]))
        y1 = max(0, int(face[1]))
        x2 = min(w, int(face[0] + face[2]))
        y2 = min(h, int(face[1] + face[3]))
        bbox = np.array([x1, y1, x2, y2], dtype=np.float32)

        # ── Face area check ──────────────────────────────────────────────
        frame_area = h * w
        face_area_ratio = (face[2] * face[3]) / frame_area

        if face_area_ratio < MIN_FACE_AREA_RATIO:
            return DetectionResult(
                face_detected=True,
                face_confidence=confidence,
                rejection_reason=f"face_too_small:{face_area_ratio:.3f}",
            )

        # ── 5-point landmarks ────────────────────────────────────────────
        # YuNet gives landmarks in person's coordinate convention.
        # Mapping to ArcFace reference landmark order:
        #   ref[0] = viewer's left eye  = person's right eye = YuNet indices 4,5
        #   ref[1] = viewer's right eye = person's left eye  = YuNet indices 6,7
        #   ref[2] = nose tip                                = YuNet indices 8,9
        #   ref[3] = viewer's left mouth = person's right    = YuNet indices 10,11
        #   ref[4] = viewer's right mouth = person's left    = YuNet indices 12,13
        landmarks = np.array([
            [face[4],  face[5]],    # right eye (person's) → ArcFace ref[0]
            [face[6],  face[7]],    # left eye  (person's) → ArcFace ref[1]
            [face[8],  face[9]],    # nose tip             → ArcFace ref[2]
            [face[10], face[11]],   # right mouth (person) → ArcFace ref[3]
            [face[12], face[13]],   # left mouth  (person) → ArcFace ref[4]
        ], dtype=np.float32)

        # ── Pose estimation ──────────────────────────────────────────────
        yaw, pitch = self._estimate_pose(landmarks)

        if abs(yaw) > MAX_YAW_DEGREES:
            return DetectionResult(
                face_detected=True,
                face_confidence=confidence,
                rejection_reason=f"excessive_yaw:{yaw:.1f}",
            )

        if abs(pitch) > MAX_PITCH_DEGREES:
            return DetectionResult(
                face_detected=True,
                face_confidence=confidence,
                rejection_reason=f"excessive_pitch:{pitch:.1f}",
            )

        # ── Alignment ────────────────────────────────────────────────────
        aligned = self._align_face(image, landmarks)

        detection = FaceDetection(
            bbox=bbox,
            landmarks=landmarks,
            confidence=confidence,
            aligned_face=aligned,
            yaw=yaw,
            pitch=pitch,
            face_area_ratio=face_area_ratio,
        )

        return DetectionResult(
            face_detected=True,
            face_confidence=confidence,
            detection=detection,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Standalone DEMO
# ═══════════════════════════════════════════════════════════════════════════

def demo_single_image(image_path: str):
    detector = FaceDetector()
    img = cv2.imread(image_path)
    if img is None:
        print(f"Could not load image: {image_path}")
        return

    result = detector.detect(img)
    print(f"Detected: {result.face_detected}")
    print(f"Confidence: {result.face_confidence:.4f}")
    if result.rejection_reason:
        print(f"Rejected: {result.rejection_reason}")
    if result.detection:
        print(f"Yaw: {result.detection.yaw:.1f}°, Pitch: {result.detection.pitch:.1f}°")
        cv2.imshow("Aligned Face", result.detection.aligned_face)
        cv2.waitKey(0)


def demo_webcam_stream():
    detector = FaceDetector()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open webcam")
        return

    print("Press 'q' to quit")
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        result = detector.detect(frame)
        if result.detection:
            det = result.detection
            x1, y1, x2, y2 = det.bbox.astype(int)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            for pt in det.landmarks:
                cv2.circle(frame, tuple(pt.astype(int)), 3, (0, 0, 255), -1)
            label = f"conf={det.confidence:.2f} yaw={det.yaw:.0f} pitch={det.pitch:.0f}"
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.imshow("Aligned", cv2.resize(det.aligned_face, (224, 224)))
        else:
            cv2.putText(frame, f"No face: {result.rejection_reason}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        cv2.imshow("Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        demo_single_image(sys.argv[1])
    else:
        demo_webcam_stream()
