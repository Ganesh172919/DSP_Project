"""
vlm_pipeline.py — Hybrid Authentication Pipeline (Traditional + VLM).

This module wraps the existing AuthPipeline with VLM reasoning capabilities.
It does NOT modify the existing pipeline — it composes on top of it.

Flow:
  1. Registration: Decode video → extract frames → existing register_face
     → store embedding + select best 3 frames as VLM references
  2. Authentication: Run existing authenticate_video → if GRANT →
     call VLM Judge → fuse scores → final GRANT/DENY with reasoning

Design:
  - VLM only runs when traditional pipeline says GRANT (saves compute on attacks)
  - VLM can VETO a GRANT if it detects issues with high confidence
  - Fusion: final = 0.6 × traditional + 0.4 × VLM
  - If VLM fails/unavailable, traditional result is used as-is
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from app.pipeline import AuthPipeline, AuthResult
from app.models.vlm_reasoner import VLMReasoner, VLMJudgment, _neutral_judgment
from app.vlm_config import (
    FUSION_TRADITIONAL_WEIGHT,
    FUSION_VLM_WEIGHT,
    VLM_VETO_CONFIDENCE,
    VLM_OVERALL_THRESHOLD,
    VLM_REF_FRAME_COUNT,
    VLM_AUTH_FRAME_COUNT,
)

logger = logging.getLogger(__name__)


@dataclass
class VLMAuthResult:
    """Combined result from traditional pipeline + VLM reasoning."""
    # Traditional pipeline result
    traditional_result: AuthResult = None
    # VLM judgment (None if VLM was skipped)
    vlm_judgment: Optional[VLMJudgment] = None
    # Whether VLM was invoked
    vlm_invoked: bool = False
    # Final fused decision
    final_decision: str = "DENY"
    final_confidence: float = 0.0
    # VLM reasoning for display
    vlm_reasoning: str = ""
    vlm_model_used: str = "none"
    # Complete processing time
    total_processing_time_ms: float = 0.0
    # Whether VLM overrode the traditional decision
    vlm_override: bool = False


class VLMAuthPipeline:
    """
    Hybrid pipeline composing the existing AuthPipeline with VLM reasoning.

    This class creates and uses the existing AuthPipeline internally —
    it does NOT inherit or modify it.
    """

    def __init__(self):
        self.pipeline = AuthPipeline()
        self.vlm = VLMReasoner()
        logger.info("VLMAuthPipeline initialized (traditional pipeline + VLM reasoner)")

    def register_face_from_video(
        self,
        video_bytes: bytes,
    ) -> tuple[np.ndarray, float, float, list[np.ndarray], list[float]]:
        """
        Video-based registration pipeline.

        1. Decode video → extract frames
        2. Run existing register_face → get embedding
        3. Select best 3 frames (highest face quality) as VLM references

        Args:
            video_bytes: raw video bytes (WebM/MP4)

        Returns:
            (template, avg_liveness, avg_quality, ref_frames, ref_qualities)
        """
        # Decode video
        frames = self.pipeline._decode_video_to_frames(video_bytes)
        logger.info(f"VLM registration: decoded {len(frames)} frames from video")

        if not frames:
            raise ValueError("No frames extracted from registration video")

        # Sample frames evenly if too many (use ~10 for registration)
        if len(frames) > 15:
            indices = np.linspace(0, len(frames) - 1, 10, dtype=int)
            reg_frames = [frames[i] for i in indices]
        else:
            reg_frames = frames

        # Run existing registration pipeline
        template, avg_liveness, avg_quality = self.pipeline.register_face(
            reg_frames, skip_injection_check=True
        )

        # Select best frames for VLM reference
        ref_frames, ref_qualities = self._select_best_frames(
            frames, count=VLM_REF_FRAME_COUNT
        )

        logger.info(
            f"VLM registration complete: {len(ref_frames)} reference frames selected, "
            f"liveness={avg_liveness:.3f}, quality={avg_quality:.3f}"
        )

        return template, avg_liveness, avg_quality, ref_frames, ref_qualities

    def _select_best_frames(
        self,
        frames: list[np.ndarray],
        count: int = 3,
    ) -> tuple[list[np.ndarray], list[float]]:
        """
        Select the best `count` frames based on face detection quality.

        Returns: (selected_frames, quality_scores)
        """
        frame_scores = []

        # Score every Nth frame (don't need to process all)
        step = max(1, len(frames) // (count * 3))
        for i in range(0, len(frames), step):
            frame = frames[i]
            detection = self.pipeline.detector.detect(frame)
            if detection.face_detected and detection.detection is not None:
                frame_scores.append((i, detection.face_confidence, frame))

        if not frame_scores:
            # Fallback: take evenly spaced frames
            indices = np.linspace(0, len(frames) - 1, count, dtype=int)
            return [frames[i] for i in indices], [0.5] * count

        # Sort by quality descending, pick diverse frames
        frame_scores.sort(key=lambda x: x[1], reverse=True)

        # Also ensure temporal diversity (don't pick frames too close together)
        selected = []
        min_gap = max(1, len(frames) // (count * 2))

        for idx, quality, frame in frame_scores:
            if len(selected) >= count:
                break
            # Check temporal distance from already selected
            too_close = any(abs(idx - s[0]) < min_gap for s in selected)
            if not too_close:
                selected.append((idx, quality, frame))

        # If not enough, add remaining by quality
        if len(selected) < count:
            for idx, quality, frame in frame_scores:
                if len(selected) >= count:
                    break
                if (idx, quality, frame) not in selected:
                    selected.append((idx, quality, frame))

        selected.sort(key=lambda x: x[0])  # chronological order

        ref_frames = [s[2] for s in selected]
        ref_qualities = [s[1] for s in selected]

        return ref_frames, ref_qualities

    def authenticate_vlm(
        self,
        stored_embedding: np.ndarray,
        video_bytes: bytes,
        ref_frames: list[np.ndarray],
    ) -> VLMAuthResult:
        """
        Full hybrid authentication pipeline.

        1. Run traditional video authentication
        2. If DENY → return immediately (VLM not invoked)
        3. If GRANT → run VLM Judge on reg frames vs auth frames
        4. Fuse scores and apply VLM veto logic
        5. Return combined result with reasoning

        Args:
            stored_embedding: encrypted embedding (decrypted before calling)
            video_bytes: authentication video bytes
            ref_frames: VLM reference frames from registration

        Returns: VLMAuthResult
        """
        t_total_start = time.perf_counter()

        vlm_result = VLMAuthResult()

        # ── Step 1: Run traditional pipeline ─────────────────────────────
        trad_result = self.pipeline.authenticate_video(
            stored_embedding=stored_embedding,
            video_bytes=video_bytes,
        )
        vlm_result.traditional_result = trad_result

        logger.info(
            f"Traditional pipeline: {trad_result.decision} "
            f"(confidence={trad_result.confidence:.3f}, "
            f"time={trad_result.processing_time_ms:.0f}ms)"
        )

        # ── Step 2: If DENY, skip VLM ────────────────────────────────────
        if trad_result.decision == "DENY":
            vlm_result.final_decision = "DENY"
            vlm_result.final_confidence = trad_result.confidence
            vlm_result.vlm_reasoning = (
                f"Traditional pipeline denied authentication: "
                f"{trad_result.denial_reason}. VLM analysis was skipped."
            )
            vlm_result.total_processing_time_ms = (
                (time.perf_counter() - t_total_start) * 1000
            )
            return vlm_result

        # ── Step 3: Extract auth frames for VLM ──────────────────────────
        auth_frames = self._extract_auth_frames(video_bytes)

        if not auth_frames:
            vlm_result.final_decision = "GRANT"
            vlm_result.final_confidence = trad_result.confidence
            vlm_result.vlm_reasoning = (
                "Traditional pipeline granted access. "
                "VLM analysis skipped: could not extract auth frames."
            )
            vlm_result.total_processing_time_ms = (
                (time.perf_counter() - t_total_start) * 1000
            )
            return vlm_result

        # ── Step 4: Run VLM Judge ────────────────────────────────────────
        if not ref_frames:
            vlm_result.final_decision = "GRANT"
            vlm_result.final_confidence = trad_result.confidence
            vlm_result.vlm_reasoning = (
                "Traditional pipeline granted access. "
                "VLM analysis skipped: no reference frames available. "
                "Please re-register using VLM registration."
            )
            vlm_result.total_processing_time_ms = (
                (time.perf_counter() - t_total_start) * 1000
            )
            return vlm_result

        vlm_result.vlm_invoked = True
        judgment = self.vlm.judge_authentication(ref_frames, auth_frames)
        vlm_result.vlm_judgment = judgment
        vlm_result.vlm_model_used = judgment.model_used
        vlm_result.vlm_reasoning = judgment.reasoning

        # ── Step 5: Fuse scores ──────────────────────────────────────────
        if judgment.error:
            # VLM failed — use traditional result as-is
            vlm_result.final_decision = "GRANT"
            vlm_result.final_confidence = trad_result.confidence
            vlm_result.vlm_reasoning = (
                f"Traditional pipeline granted access (confidence: "
                f"{trad_result.confidence:.1%}). "
                f"VLM analysis encountered an error: {judgment.error}"
            )
        else:
            # Fuse traditional and VLM scores
            trad_conf = trad_result.confidence
            vlm_score = judgment.overall_score

            fused_confidence = (
                FUSION_TRADITIONAL_WEIGHT * trad_conf +
                FUSION_VLM_WEIGHT * vlm_score
            )

            logger.info(
                f"Fusion: trad={trad_conf:.3f} × {FUSION_TRADITIONAL_WEIGHT} + "
                f"vlm={vlm_score:.3f} × {FUSION_VLM_WEIGHT} = "
                f"{fused_confidence:.3f}"
            )

            # Check VLM veto conditions
            vlm_denies = (
                not judgment.same_person or
                not judgment.is_live or
                not judgment.is_authentic
            )

            # VLM high-confidence veto
            veto_confidence = 1.0 - judgment.overall_score
            if vlm_denies and veto_confidence >= VLM_VETO_CONFIDENCE:
                vlm_result.final_decision = "DENY"
                vlm_result.final_confidence = fused_confidence
                vlm_result.vlm_override = True
                vlm_result.vlm_reasoning = (
                    f"⚠️ VLM OVERRIDE: Traditional pipeline granted access, "
                    f"but VLM analysis raised critical concerns "
                    f"(confidence: {veto_confidence:.1%}). "
                    f"\n\nVLM Analysis: {judgment.reasoning}"
                )
                if judgment.red_flags:
                    vlm_result.vlm_reasoning += (
                        f"\n\n🚩 Red Flags: {', '.join(judgment.red_flags)}"
                    )
            elif vlm_score < VLM_OVERALL_THRESHOLD and vlm_denies:
                # VLM is concerned but not confident enough to veto
                vlm_result.final_decision = "GRANT"
                vlm_result.final_confidence = fused_confidence
                vlm_result.vlm_reasoning = (
                    f"✅ Access granted with caution. "
                    f"Traditional pipeline is confident "
                    f"({trad_conf:.1%}), but VLM flagged potential concerns "
                    f"(VLM score: {vlm_score:.1%})."
                    f"\n\nVLM Analysis: {judgment.reasoning}"
                )
            else:
                # Both agree — GRANT
                vlm_result.final_decision = "GRANT"
                vlm_result.final_confidence = fused_confidence
                vlm_result.vlm_reasoning = (
                    f"✅ Authentication verified by both traditional pipeline "
                    f"({trad_conf:.1%}) and VLM reasoning ({vlm_score:.1%}). "
                    f"\n\nVLM Analysis: {judgment.reasoning}"
                )

        vlm_result.total_processing_time_ms = (
            (time.perf_counter() - t_total_start) * 1000
        )

        logger.info(
            f"VLM hybrid decision: {vlm_result.final_decision} "
            f"(fused_conf={vlm_result.final_confidence:.3f}, "
            f"vlm_override={vlm_result.vlm_override}, "
            f"vlm_model={vlm_result.vlm_model_used}, "
            f"total_time={vlm_result.total_processing_time_ms:.0f}ms)"
        )

        return vlm_result

    def _extract_auth_frames(
        self,
        video_bytes: bytes,
        count: int = None,
    ) -> list[np.ndarray]:
        """Extract authentication frames from video for VLM analysis."""
        if count is None:
            count = VLM_AUTH_FRAME_COUNT

        frames = self.pipeline._decode_video_to_frames(video_bytes)
        if not frames:
            return []

        # Select evenly spaced frames
        indices = np.linspace(0, len(frames) - 1, count, dtype=int)
        return [frames[i] for i in indices]

    def get_vlm_status(self) -> dict:
        """Get VLM model status."""
        return self.vlm.get_status()
