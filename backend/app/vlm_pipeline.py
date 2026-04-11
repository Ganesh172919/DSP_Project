"""
vlm_pipeline.py — Pure VLM authentication pipeline.

This is a SEPARATE auth path from the traditional 5-layer pipeline.
It sends registration frames + authentication frames directly to a VLM
and gets back identity/liveness reasoning via prompt engineering.

Two auth paths in the system:
  1. Traditional (existing) — /api/v1/authenticate → ML pipeline
  2. VLM (this module)     — /api/v1/vlm/authenticate → VLM reasoning

This module is ADDITIVE — does not modify any existing pipeline code.
"""

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ─── Result Dataclass ───────────────────────────────────────────────────────

@dataclass
class VLMAuthResult:
    """Result from pure VLM authentication."""
    decision: str = "DENY"           # GRANT or DENY
    confidence: float = 0.0

    # VLM judgment details
    same_person: bool = False
    same_person_confidence: float = 0.0
    is_live: bool = False
    liveness_confidence: float = 0.0
    is_authentic: bool = False
    authenticity_confidence: float = 0.0

    reasoning: str = ""              # VLM's natural language reasoning
    red_flags: list = field(default_factory=list)
    model_used: str = "none"
    processing_time_ms: float = 0.0
    error: Optional[str] = None


class VLMAuthPipeline:
    """
    Pure VLM authentication pipeline.

    Registration: store face frames to disk.
    Authentication: send reg frames + auth frames to VLM → get reasoning.

    The VLM acts as the sole decision-maker in this path.
    """

    def __init__(self):
        self._vlm = None
        logger.info("VLMAuthPipeline initialized (lazy loading)")

    def _get_vlm(self):
        """Lazy-load the VLM Reasoner (downloads model on first call)."""
        if self._vlm is None:
            from app.models.vlm_reasoner import VLMReasoner
            self._vlm = VLMReasoner()
        return self._vlm

    # ═════════════════════════════════════════════════════════════════════
    # VLM AUTHENTICATION — pure VLM reasoning
    # ═════════════════════════════════════════════════════════════════════

    def authenticate(
        self,
        ref_frames: list[np.ndarray],
        auth_frames: list[np.ndarray],
    ) -> VLMAuthResult:
        """
        Pure VLM authentication — compare registration vs auth frames.

        Args:
            ref_frames: registration reference frames (from disk)
            auth_frames: authentication frames (from video/images)

        Returns:
            VLMAuthResult with VLM's decision and reasoning
        """
        t_start = time.perf_counter()
        result = VLMAuthResult()

        if not ref_frames:
            result.reasoning = "No reference frames found. Please register first using VLM Register."
            result.error = "no_ref_frames"
            result.processing_time_ms = (time.perf_counter() - t_start) * 1000
            return result

        if not auth_frames:
            result.reasoning = "No authentication frames extracted. Please try again."
            result.error = "no_auth_frames"
            result.processing_time_ms = (time.perf_counter() - t_start) * 1000
            return result

        try:
            vlm = self._get_vlm()
            judgment = vlm.judge_authentication(ref_frames, auth_frames)

            result.same_person = judgment.same_person
            result.same_person_confidence = judgment.same_person_confidence
            result.is_live = judgment.is_live
            result.liveness_confidence = judgment.liveness_confidence
            result.is_authentic = judgment.is_authentic
            result.authenticity_confidence = judgment.authenticity_confidence
            result.confidence = judgment.overall_score
            result.reasoning = judgment.reasoning
            result.red_flags = judgment.red_flags
            result.model_used = judgment.model_used

            # VLM decision: GRANT if all checks pass and overall > threshold
            from app.vlm_config import VLM_OVERALL_THRESHOLD
            if (
                judgment.same_person
                and judgment.is_live
                and judgment.is_authentic
                and judgment.overall_score >= VLM_OVERALL_THRESHOLD
            ):
                result.decision = "GRANT"
            else:
                result.decision = "DENY"

            logger.info(
                f"VLM auth: decision={result.decision}, "
                f"same={judgment.same_person}({judgment.same_person_confidence:.2f}), "
                f"live={judgment.is_live}({judgment.liveness_confidence:.2f}), "
                f"authentic={judgment.is_authentic}({judgment.authenticity_confidence:.2f}), "
                f"overall={judgment.overall_score:.2f}, "
                f"model={judgment.model_used}, "
                f"time={judgment.inference_time_ms:.0f}ms"
            )

        except Exception as e:
            logger.error(f"VLM authentication failed: {e}", exc_info=True)
            result.reasoning = f"VLM analysis error: {str(e)[:300]}"
            result.error = str(e)[:200]

        result.processing_time_ms = (time.perf_counter() - t_start) * 1000
        return result

    def authenticate_from_video(
        self,
        ref_frames: list[np.ndarray],
        video_bytes: bytes,
        num_auth_frames: int = 3,
    ) -> VLMAuthResult:
        """
        Authenticate by extracting frames from video and sending to VLM.

        Args:
            ref_frames: registration reference frames (from disk)
            video_bytes: raw video bytes from webcam (WebM/MP4)
            num_auth_frames: how many frames to extract from video

        Returns:
            VLMAuthResult with VLM's decision and reasoning
        """
        auth_frames = self._extract_frames_from_video(video_bytes, num_auth_frames)
        return self.authenticate(ref_frames, auth_frames)

    # ═════════════════════════════════════════════════════════════════════
    # VLM STATUS
    # ═════════════════════════════════════════════════════════════════════

    def get_vlm_status(self) -> dict:
        """Return VLM model status info."""
        try:
            vlm = self._get_vlm()
            return vlm.get_status()
        except Exception as e:
            return {"loaded": False, "error": str(e)}

    # ═════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═════════════════════════════════════════════════════════════════════

    @staticmethod
    def _extract_frames_from_video(
        video_bytes: bytes,
        count: int = 3,
    ) -> list[np.ndarray]:
        """Extract evenly spaced frames from video bytes."""
        tmp_path = os.path.join("data", f"tmp_vlm_{uuid.uuid4().hex}.webm")
        try:
            os.makedirs("data", exist_ok=True)
            with open(tmp_path, "wb") as f:
                f.write(video_bytes)

            cap = cv2.VideoCapture(tmp_path)
            if not cap.isOpened():
                logger.warning("Cannot open video for VLM frame extraction")
                return []

            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total < 1:
                cap.release()
                return []

            indices = np.linspace(0, total - 1, min(count, total), dtype=int)
            frames = []

            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                ret, frame = cap.read()
                if ret:
                    frames.append(frame)

            cap.release()
            logger.info(f"Extracted {len(frames)} frames from video ({total} total)")
            return frames

        except Exception as e:
            logger.error(f"Frame extraction failed: {e}")
            return []
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
