"""
pipeline.py — Decision Engine

Orchestrates all 5 AI layers into a single authentication pipeline:
  Layer 0: Anti-Injection Guard
  Layer 1: Face Detection & Alignment
  Layer 2: ArcFace Recognition
  Layer 3: Liveness (CNN + rPPG + Training-Free Anti-Spoof)
  Layer 4: Deepfake Detection (Spectral + CNN + Training-Free)
  Layer 5: Instruction Compliance Verification (NEW)

Decision logic:
  1. if injection.is_real_camera is False      → DENY (virtual_camera)
  2. if detection.face_confidence < 0.9        → DENY (no_face)
  3. if liveness.final_score < 0.70            → DENY (liveness_fail)
  4. if deepfake.score > 0.30                  → DENY (synthetic_face)
  5. if any instruction failed                 → DENY (instruction_fail)
  6. if recognition.similarity < 0.40          → DENY (identity_mismatch)
  ELSE → GRANT

Returns: AuthResult with decision, confidence, threat_flags, and all scores.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from app.models.anti_injection import AntiInjectionGuard, InjectionResult
from app.models.detector import FaceDetector, DetectionResult
from app.models.recognizer import FaceRecognizer, RecognitionResult
from app.models.liveness import LivenessDetector, LivenessResult
from app.models.deepfake import DeepfakeDetector, DeepfakeResult
from app.models.instruction_verifier import InstructionVerifier, InstructionResult
from app.instructions import get_instruction
from app.video_utils import decode_video_bytes
from app.config import (
    FACE_CONFIDENCE_THRESHOLD, FUSION_FINAL_THRESHOLD,
    DEEPFAKE_FLAG_THRESHOLD, SIMILARITY_THRESHOLD,
    INSTRUCTION_MIN_CONFIDENCE,
)

logger = logging.getLogger(__name__)


@dataclass
class AuthScores:
    injection_confidence: float = 0.0
    face_confidence: float = 0.0
    liveness_score: float = 0.0
    deepfake_score: float = 0.0
    similarity_score: float = 0.0
    instruction_scores: list[float] = field(default_factory=list)


@dataclass
class AuthResult:
    decision: str                        # "GRANT" or "DENY"
    confidence: float = 0.0             # weighted mean of all scores
    threat_flags: list[str] = field(default_factory=list)
    scores: AuthScores = field(default_factory=AuthScores)
    denial_reason: Optional[str] = None
    processing_time_ms: float = 0.0

    # Sub-results for detailed inspection
    injection_result: Optional[InjectionResult] = None
    detection_result: Optional[DetectionResult] = None
    recognition_result: Optional[RecognitionResult] = None
    liveness_result: Optional[LivenessResult] = None
    deepfake_result: Optional[DeepfakeResult] = None
    instruction_results: list[InstructionResult] = field(default_factory=list)


class AuthPipeline:
    """
    Production authentication pipeline — runs all 5 layers sequentially
    with early-exit on failure.
    """

    def __init__(self):
        self.injection_guard = AntiInjectionGuard()
        self.detector = FaceDetector()
        self.recognizer = FaceRecognizer()
        self.liveness = LivenessDetector()
        self.deepfake = DeepfakeDetector()
        self.instruction_verifier = InstructionVerifier()

        logger.info("AuthPipeline initialized — all 5 layers ready")

    def decide(
        self,
        detection: DetectionResult,
        liveness: LivenessResult,
        deepfake: DeepfakeResult,
        injection: InjectionResult,
        recognition: RecognitionResult,
        instruction_results: Optional[list[InstructionResult]] = None,
    ) -> AuthResult:
        """
        Core decision function — cascading deny checks with confidence calculation.
        """
        threat_flags = []
        inst_scores = [r.confidence for r in (instruction_results or [])]
        scores = AuthScores(
            injection_confidence=injection.confidence,
            face_confidence=detection.face_confidence,
            liveness_score=liveness.final_score,
            deepfake_score=deepfake.deepfake_probability,
            similarity_score=recognition.similarity,
            instruction_scores=inst_scores,
        )

        # Collect threat flags
        threat_flags.extend(injection.flags)

        # ── Check 1: Virtual camera ──────────────────────────────────────
        if not injection.is_real_camera:
            threat_flags.append("virtual_camera")
            return AuthResult(
                decision="DENY",
                confidence=0.0,
                threat_flags=threat_flags,
                scores=scores,
                denial_reason="virtual_camera",
            )

        # ── Check 2: No valid face ───────────────────────────────────────
        if not detection.face_detected or detection.face_confidence < FACE_CONFIDENCE_THRESHOLD:
            threat_flags.append("no_face")
            return AuthResult(
                decision="DENY",
                confidence=0.0,
                threat_flags=threat_flags,
                scores=scores,
                denial_reason="no_face",
            )

        # ── Check 3: Liveness failure ────────────────────────────────────
        if liveness.final_score < FUSION_FINAL_THRESHOLD:
            threat_flags.append("liveness_fail")
            return AuthResult(
                decision="DENY",
                confidence=liveness.final_score,
                threat_flags=threat_flags,
                scores=scores,
                denial_reason="liveness_fail",
            )

        # ── Check 4: Deepfake detected ──────────────────────────────────
        if deepfake.deepfake_probability > DEEPFAKE_FLAG_THRESHOLD:
            threat_flags.append("synthetic_face")
            threat_flags.extend(deepfake.flags)
            return AuthResult(
                decision="DENY",
                confidence=1.0 - deepfake.deepfake_probability,
                threat_flags=threat_flags,
                scores=scores,
                denial_reason="synthetic_face",
            )

        # ── Check 5: Instruction compliance ─────────────────────────────
        if instruction_results:
            for ir in instruction_results:
                if not ir.passed or ir.confidence < INSTRUCTION_MIN_CONFIDENCE:
                    threat_flags.append(f"instruction_fail:{ir.instruction_id}")
                    return AuthResult(
                        decision="DENY",
                        confidence=ir.confidence,
                        threat_flags=threat_flags,
                        scores=scores,
                        denial_reason="instruction_fail",
                        instruction_results=instruction_results,
                    )

        # ── Check 6: Identity mismatch ───────────────────────────────────
        if recognition.similarity < SIMILARITY_THRESHOLD:
            threat_flags.append("identity_mismatch")
            return AuthResult(
                decision="DENY",
                confidence=recognition.similarity,
                threat_flags=threat_flags,
                scores=scores,
                denial_reason="identity_mismatch",
            )

        # ── ALL CHECKS PASSED → GRANT ────────────────────────────────────
        confidence_components = [
            liveness.final_score,
            recognition.similarity,
            1.0 - deepfake.deepfake_probability,
        ]
        if inst_scores:
            confidence_components.extend(inst_scores)

        confidence = float(np.mean(confidence_components))

        return AuthResult(
            decision="GRANT",
            confidence=round(confidence, 4),
            threat_flags=threat_flags,
            scores=scores,
            instruction_results=instruction_results or [],
        )

    def _decode_video_to_frames(self, video_bytes: bytes) -> list[np.ndarray]:
        """Decode video bytes (WebM/MP4) to a list of BGR frames."""
        try:
            frames = decode_video_bytes(video_bytes, suffix=".webm")
        except Exception as e:
            logger.error(f"Video decode error: {e}")
            frames = []

        logger.info(f"Decoded {len(frames)} frames from video")
        return frames

    def authenticate_with_challenges(
        self,
        stored_embedding: np.ndarray,
        instruction_ids: list[int],
        video_data_list: list[bytes],
        face_frame: Optional[np.ndarray] = None,
        skip_injection_check: bool = True,
    ) -> AuthResult:
        """
        Full authentication pipeline with instruction challenges.

        Args:
            stored_embedding: the registered user's 512-d template
            instruction_ids: list of instruction IDs to verify
            video_data_list: list of video bytes (one per instruction)
            face_frame: optional still frame for recognition (if not using video)
            skip_injection_check: skip Layer 0 for web uploads

        Returns: AuthResult
        """
        t_start = time.perf_counter()

        # ── Layer 0: Anti-Injection (skip for web) ───────────────────────
        injection = InjectionResult(is_real_camera=True, confidence=1.0, flags=[])

        # ── Decode all videos to frames ──────────────────────────────────
        all_video_frames = []
        for idx, video_bytes in enumerate(video_data_list):
            frames = self._decode_video_to_frames(video_bytes)
            all_video_frames.append(frames)
            logger.info(f"Video {idx}: {len(frames)} frames")

        # Use first video's first frame for face detection if no face_frame
        primary_frame = face_frame
        if primary_frame is None:
            for vf in all_video_frames:
                if vf:
                    primary_frame = vf[len(vf) // 2]  # use middle frame
                    break

        if primary_frame is None:
            result = AuthResult(decision="DENY", denial_reason="no_frames")
            result.processing_time_ms = (time.perf_counter() - t_start) * 1000
            return result

        # ── Layer 1: Face Detection & Alignment ──────────────────────────
        detection = self.detector.detect(primary_frame)

        if not detection.face_detected or detection.detection is None:
            result = self.decide(
                detection,
                LivenessResult(0, rppg=None, final_score=0),
                DeepfakeResult(is_deepfake=False, deepfake_probability=0.0),
                injection,
                RecognitionResult(np.zeros(512)),
            )
            result.injection_result = injection
            result.detection_result = detection
            result.processing_time_ms = (time.perf_counter() - t_start) * 1000
            return result

        aligned_face = detection.detection.aligned_face
        landmarks = detection.detection.landmarks

        # ── Layer 2: ArcFace Recognition ─────────────────────────────────
        embedding = self.recognizer.extract_embedding(aligned_face)
        recognition = self.recognizer.match_against_template(embedding, stored_embedding)

        # ── Collect all frames for multi-frame analysis ──────────────────
        all_frames = []
        for vf in all_video_frames:
            all_frames.extend(vf)

        # Collect FaceMesh landmarks across frames for liveness
        face_landmarks_seq = []
        for frame in all_frames[::5]:  # every 5th frame for speed
            lms = self.instruction_verifier.face_analyzer.get_landmarks(frame)
            face_landmarks_seq.append(lms)

        # ── Layer 5: Instruction Verification (before liveness — feeds score) ─
        instruction_results = []
        instruction_scores_avg = 1.0
        for idx, (inst_id, video_frames) in enumerate(zip(instruction_ids, all_video_frames)):
            inst = get_instruction(inst_id)
            if inst is None:
                instruction_results.append(InstructionResult(
                    inst_id, False, 0.0, "Unknown instruction"))
                continue

            result = self.instruction_verifier.verify(
                video_frames, inst_id, inst["verify_key"]
            )
            instruction_results.append(result)
            logger.info(f"Instruction {inst_id} ({inst['verify_key']}): "
                        f"passed={result.passed}, confidence={result.confidence:.3f}")

        if instruction_results:
            instruction_scores_avg = float(np.mean([r.confidence for r in instruction_results]))

        # ── Layer 3: Liveness ────────────────────────────────────────────
        liveness = self.liveness.check_full(
            aligned_face,
            frames=all_frames if all_frames else None,
            face_landmarks=landmarks,
            instruction_score=instruction_scores_avg,
            face_landmarks_sequence=face_landmarks_seq if face_landmarks_seq else None,
        )

        # ── Layer 4: Deepfake Detection ──────────────────────────────────
        deepfake = self.deepfake.detect(
            aligned_face,
            frames=all_frames if all_frames else None,
        )

        # ── Decision ─────────────────────────────────────────────────────
        result = self.decide(
            detection, liveness, deepfake, injection,
            recognition, instruction_results,
        )
        result.injection_result = injection
        result.detection_result = detection
        result.recognition_result = recognition
        result.liveness_result = liveness
        result.deepfake_result = deepfake
        result.instruction_results = instruction_results
        result.processing_time_ms = (time.perf_counter() - t_start) * 1000

        logger.info(
            f"Auth decision: {result.decision} | "
            f"confidence={result.confidence:.3f} | "
            f"liveness={liveness.final_score:.3f} | "
            f"deepfake={deepfake.deepfake_probability:.3f} | "
            f"similarity={recognition.similarity:.3f} | "
            f"instructions={[r.passed for r in instruction_results]} | "
            f"processing={result.processing_time_ms:.0f}ms"
        )

        return result

    def authenticate(
        self,
        frame: np.ndarray,
        stored_embedding: np.ndarray,
        cap: Optional[cv2.VideoCapture] = None,
        frames_for_liveness: Optional[list[np.ndarray]] = None,
        skip_injection_check: bool = False,
    ) -> AuthResult:
        """
        Legacy authentication pipeline on a single frame (no instructions).
        Kept for backward compatibility.
        """
        t_start = time.perf_counter()

        # ── Layer 0: Anti-Injection ──────────────────────────────────────
        injection = InjectionResult(is_real_camera=True, confidence=1.0, flags=[])
        if not skip_injection_check:
            if cap is not None:
                injection = self.injection_guard.validate(cap)
            else:
                injection = self.injection_guard.validate(camera_index=0)

        if not injection.is_real_camera:
            result = self.decide(
                DetectionResult(False),
                LivenessResult(0, rppg=None, final_score=0),
                DeepfakeResult(is_deepfake=False, deepfake_probability=0.0),
                injection,
                RecognitionResult(np.zeros(512)),
            )
            result.injection_result = injection
            result.processing_time_ms = (time.perf_counter() - t_start) * 1000
            return result

        # ── Layer 1: Face Detection & Alignment ──────────────────────────
        detection = self.detector.detect(frame)

        if not detection.face_detected or detection.detection is None:
            result = self.decide(
                detection,
                LivenessResult(0, rppg=None, final_score=0),
                DeepfakeResult(is_deepfake=False, deepfake_probability=0.0),
                injection,
                RecognitionResult(np.zeros(512)),
            )
            result.injection_result = injection
            result.detection_result = detection
            result.processing_time_ms = (time.perf_counter() - t_start) * 1000
            return result

        aligned_face = detection.detection.aligned_face
        landmarks = detection.detection.landmarks

        # ── Layer 2: ArcFace Recognition ─────────────────────────────────
        embedding = self.recognizer.extract_embedding(aligned_face)
        recognition = self.recognizer.match_against_template(embedding, stored_embedding)

        # ── Layer 3: Liveness ────────────────────────────────────────────
        liveness = self.liveness.check_full(
            aligned_face,
            frames=frames_for_liveness,
            face_landmarks=landmarks,
        )

        # ── Layer 4: Deepfake Detection ──────────────────────────────────
        deepfake = self.deepfake.detect(aligned_face)

        # ── Decision ─────────────────────────────────────────────────────
        result = self.decide(detection, liveness, deepfake, injection, recognition)
        result.injection_result = injection
        result.detection_result = detection
        result.recognition_result = recognition
        result.liveness_result = liveness
        result.deepfake_result = deepfake
        result.processing_time_ms = (time.perf_counter() - t_start) * 1000

        logger.info(
            f"Auth decision: {result.decision} | "
            f"confidence={result.confidence:.3f} | "
            f"processing={result.processing_time_ms:.0f}ms | "
            f"flags={result.threat_flags}"
        )

        return result

    def authenticate_video(
        self,
        stored_embedding: np.ndarray,
        video_bytes: bytes,
        skip_injection_check: bool = True,
    ) -> AuthResult:
        """
        Video-based authentication pipeline (no instructions).

        Accepts raw video bytes, extracts frames, runs all layers:
          - Middle frame for face detection + ArcFace recognition
          - All frames for liveness (multi-frame analysis)
          - Middle frame for deepfake detection

        Returns: AuthResult
        """
        t_start = time.perf_counter()

        # ── Decode video to frames ───────────────────────────────────────
        frames = self._decode_video_to_frames(video_bytes)
        logger.info(f"Video auth: {len(frames)} frames extracted")

        if not frames:
            result = AuthResult(decision="DENY", denial_reason="no_frames")
            result.processing_time_ms = (time.perf_counter() - t_start) * 1000
            return result

        # Use middle frame for face detection/recognition
        primary_frame = frames[len(frames) // 2]

        # ── Layer 0: Anti-Injection (skipped for web uploads) ────────────
        injection = InjectionResult(is_real_camera=True, confidence=1.0, flags=[])

        # ── Layer 1: Face Detection & Alignment ─────────────────────────
        detection = self.detector.detect(primary_frame)

        if not detection.face_detected or detection.detection is None:
            result = self.decide(
                detection,
                LivenessResult(),
                DeepfakeResult(is_deepfake=False, deepfake_probability=0.0),
                injection,
                RecognitionResult(np.zeros(512)),
            )
            result.injection_result = injection
            result.detection_result = detection
            result.processing_time_ms = (time.perf_counter() - t_start) * 1000
            return result

        aligned_face = detection.detection.aligned_face
        landmarks = detection.detection.landmarks

        # ── Layer 2: ArcFace Recognition ────────────────────────────────
        embedding = self.recognizer.extract_embedding(aligned_face)
        recognition = self.recognizer.match_against_template(embedding, stored_embedding)

        # ── Layer 3: Liveness (using ALL video frames) ──────────────────
        liveness = self.liveness.check_full(
            aligned_face,
            frames=frames,  # pass all video frames for multi-frame analysis
            face_landmarks=landmarks,
        )

        # ── Layer 4: Deepfake Detection ─────────────────────────────────
        deepfake = self.deepfake.detect(
            aligned_face,
            frames=frames if len(frames) > 1 else None,
        )

        # ── Decision (no instructions) ──────────────────────────────────
        result = self.decide(detection, liveness, deepfake, injection, recognition)
        result.injection_result = injection
        result.detection_result = detection
        result.recognition_result = recognition
        result.liveness_result = liveness
        result.deepfake_result = deepfake
        result.processing_time_ms = (time.perf_counter() - t_start) * 1000

        logger.info(
            f"Video auth decision: {result.decision} | "
            f"confidence={result.confidence:.3f} | "
            f"liveness={liveness.final_score:.3f} | "
            f"deepfake={deepfake.deepfake_probability:.3f} | "
            f"similarity={recognition.similarity:.3f} | "
            f"frames={len(frames)} | "
            f"processing={result.processing_time_ms:.0f}ms"
        )

        return result

    def register_face(
        self,
        frames: list[np.ndarray],
        skip_injection_check: bool = False,
        cap: Optional[cv2.VideoCapture] = None,
    ) -> tuple[np.ndarray, float, float]:
        """
        Registration pipeline: extract and average embeddings from multiple frames.

        Args:
            frames: list of BGR images (5 recommended)
            skip_injection_check: skip Layer 0
            cap: VideoCapture for injection checking

        Returns: (averaged_embedding, avg_liveness_score, avg_face_quality)
        """
        # Optional injection check
        if not skip_injection_check and cap is not None:
            injection = self.injection_guard.validate(cap)
            if not injection.is_real_camera:
                raise ValueError(f"Virtual camera detected: {injection.flags}")

        aligned_faces = []
        liveness_scores = []
        face_qualities = []

        for frame in frames:
            detection = self.detector.detect(frame)
            if detection.detection is None:
                logger.warning("Frame rejected during registration — no valid face")
                continue

            aligned = detection.detection.aligned_face
            aligned_faces.append(aligned)
            face_qualities.append(detection.face_confidence)

            # Quick liveness check on each frame
            liveness_score = self.liveness.check_single_frame(aligned)
            liveness_scores.append(liveness_score)

        if len(aligned_faces) < 1:
            raise ValueError(f"No valid face detected in any frame (0/{len(frames)} passed)")

        # Compute averaged template
        template = self.recognizer.compute_template(aligned_faces)

        avg_liveness = float(np.mean(liveness_scores))
        avg_quality = float(np.mean(face_qualities))

        return template, avg_liveness, avg_quality
