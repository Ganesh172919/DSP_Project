"""
vlm_routes.py — FastAPI router for VLM-enhanced authentication endpoints.

This module is ADDITIVE — it does not modify existing routes.
All VLM endpoints are mounted under /api/v1/vlm/.

Flow:
  - VLM Register: same 5-frame capture as normal register + saves reference frames to disk
  - VLM Authenticate: same video auth as existing + VLM Judge layer after GRANT

Endpoints:
  POST /api/v1/vlm/register       — Register with 5 face images + store VLM ref frames
  POST /api/v1/vlm/authenticate   — Video auth + VLM reasoning after GRANT
  GET  /api/v1/vlm/status         — VLM model status
"""

import logging
from typing import Optional, List

import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import RATE_LIMIT
from app.db.models import get_db
from app.db import crud
from app.db.vlm_crud import (
    store_vlm_reference_frames,
    get_vlm_reference_frames,
    has_vlm_reference_frames,
)
from app.crypto import encrypt_embedding, decrypt_embedding, create_jwt

logger = logging.getLogger(__name__)

# ─── Router ─────────────────────────────────────────────────────────────────
vlm_router = APIRouter(prefix="/api/v1/vlm", tags=["VLM Authentication"])

# ─── Lazy pipeline references ──────────────────────────────────────────────
_vlm_pipeline = None
_base_pipeline = None


def _get_base_pipeline():
    """Get the existing AuthPipeline (same one used by main.py)."""
    global _base_pipeline
    if _base_pipeline is None:
        from app.pipeline import AuthPipeline
        _base_pipeline = AuthPipeline()
    return _base_pipeline


def _get_vlm_reasoner():
    """Get the VLM reasoner (lazy init — downloads model on first call)."""
    global _vlm_pipeline
    if _vlm_pipeline is None:
        from app.models.vlm_reasoner import VLMReasoner
        _vlm_pipeline = VLMReasoner()
    return _vlm_pipeline


# ═══════════════════════════════════════════════════════════════════════════
# VLM REGISTRATION — same 5-frame capture as normal register
# ═══════════════════════════════════════════════════════════════════════════

@vlm_router.post("/register")
async def vlm_register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    face_data: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Register a user with face images + VLM reference frames.

    Same interface as /api/v1/register (accepts multiple face images).
    Additionally stores the face frames on disk for VLM comparison.

    Accepts:
      - username: unique username
      - email: unique email
      - face_data: list of face image files (5 recommended, same as normal register)

    Returns:
      {user_id, username, liveness_score, face_quality, vlm_ref_frames_stored, status}
    """
    # Check if user already exists
    existing = crud.get_user_by_username(db, username)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Username '{username}' already registered"
        )

    existing_email = crud.get_user_by_email(db, email)
    if existing_email:
        raise HTTPException(
            status_code=409,
            detail=f"Email '{email}' already registered"
        )

    # Decode all uploaded images into frames
    frames = []
    for upload in face_data:
        content = await upload.read()
        img = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is not None:
            frames.append(img)

    if len(frames) < 1:
        raise HTTPException(status_code=400, detail="No valid images uploaded")

    logger.info(f"VLM Registration: received {len(frames)} frames for user '{username}'")

    try:
        pipe = _get_base_pipeline()

        # Run existing registration pipeline (same as normal register)
        template, liveness_score, face_quality = pipe.register_face(
            frames, skip_injection_check=True
        )

        # Encrypt embedding
        encrypted = encrypt_embedding(template)

        # Store user in DB (same as existing registration)
        user = crud.create_user(
            db=db,
            username=username,
            email=email,
            embedding_enc=encrypted,
            face_quality=face_quality,
        )

        # Also store the frames on disk for VLM reference
        qualities = [face_quality] * len(frames)  # use avg quality for all
        vlm_count = store_vlm_reference_frames(
            db=db,
            user_id=user.id,
            frames=frames,
            qualities=qualities,
        )

        logger.info(
            f"VLM registered user '{username}' (id={user.id}): "
            f"{vlm_count} ref frames stored on disk"
        )

        return {
            "user_id": user.id,
            "username": username,
            "liveness_score": round(liveness_score, 4),
            "face_quality": round(face_quality, 4),
            "vlm_ref_frames_stored": vlm_count,
            "status": "registered",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"VLM registration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"VLM registration failed: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# VLM AUTHENTICATION — video auth + VLM reasoning after GRANT
# ═══════════════════════════════════════════════════════════════════════════

@vlm_router.post("/authenticate")
async def vlm_authenticate(
    request: Request,
    username: str = Form(...),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    VLM-enhanced video authentication.

    Same video input as /api/v1/authenticate/video.
    After traditional pipeline says GRANT, VLM Judge reviews the frames.

    Pipeline:
      1. Run traditional video authentication (all existing layers)
      2. If traditional says DENY → return immediately (VLM skipped)
      3. If traditional says GRANT → extract auth frames + load ref frames
      4. Send both to VLM for semantic reasoning
      5. Return combined result with VLM reasoning text

    Accepts:
      - username: registered username
      - video: 5-second webcam video (WebM/MP4)

    Returns:
      {authenticated, confidence, vlm_reasoning, scores, processing_time_ms, ...}
    """
    import time
    t_start = time.perf_counter()

    # Look up user
    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User '{username}' not found"
        )

    # Decrypt stored embedding
    stored_embedding = decrypt_embedding(user.embedding_enc)

    # Read video bytes
    video_bytes = await video.read()
    if not video_bytes:
        raise HTTPException(status_code=400, detail="Empty video file")

    logger.info(f"VLM auth for '{username}': video={len(video_bytes)} bytes")

    # ── Step 1: Run traditional video pipeline ──────────────────────────
    pipe = _get_base_pipeline()
    trad_result = pipe.authenticate_video(
        stored_embedding=stored_embedding,
        video_bytes=video_bytes,
    )

    trad_scores = {
        "liveness": trad_result.scores.liveness_score,
        "deepfake": trad_result.scores.deepfake_score,
        "similarity": trad_result.scores.similarity_score,
        "injection": trad_result.scores.injection_confidence,
    }

    logger.info(
        f"Traditional pipeline: {trad_result.decision} "
        f"(confidence={trad_result.confidence:.3f})"
    )

    # ── Step 2: If DENY, skip VLM ──────────────────────────────────────
    if trad_result.decision == "DENY":
        total_ms = (time.perf_counter() - t_start) * 1000

        # Log to audit table
        _log_auth(db, request, user, trad_result, "DENY", None)

        return {
            "authenticated": False,
            "confidence": round(trad_result.confidence, 4),
            "vlm_reasoning": (
                f"Traditional pipeline denied authentication: "
                f"{trad_result.denial_reason}. VLM analysis was skipped."
            ),
            "vlm_model_used": "none",
            "vlm_invoked": False,
            "vlm_override": False,
            "has_vlm_refs": has_vlm_reference_frames(db, user.id),
            "scores": {"traditional": trad_scores, "vlm": {}},
            "threat_flags": trad_result.threat_flags,
            "processing_time_ms": round(total_ms, 1),
            "traditional_decision": "DENY",
            "traditional_confidence": round(trad_result.confidence, 4),
            "denial_reason": trad_result.denial_reason,
        }

    # ── Step 3: GRANT — invoke VLM Judge ───────────────────────────────
    # Load reference frames from disk
    ref_frames = get_vlm_reference_frames(db, user.id)
    has_refs = len(ref_frames) > 0

    # Extract auth frames from the video
    auth_frames = _extract_frames_from_video(video_bytes, count=3)

    vlm_reasoning = ""
    vlm_scores = {}
    vlm_invoked = False
    vlm_override = False
    vlm_model = "none"
    final_decision = "GRANT"
    final_confidence = trad_result.confidence

    if has_refs and auth_frames:
        try:
            vlm = _get_vlm_reasoner()
            judgment = vlm.judge_authentication(ref_frames, auth_frames)
            vlm_invoked = True
            vlm_model = judgment.model_used

            vlm_scores = {
                "vlm_identity": judgment.same_person_confidence,
                "vlm_liveness": judgment.liveness_confidence,
                "vlm_authenticity": judgment.authenticity_confidence,
                "vlm_overall": judgment.overall_score,
            }

            # Fusion: 0.6 × traditional + 0.4 × VLM
            from app.vlm_config import (
                FUSION_TRADITIONAL_WEIGHT, FUSION_VLM_WEIGHT,
                VLM_VETO_CONFIDENCE,
            )

            fused = (
                FUSION_TRADITIONAL_WEIGHT * trad_result.confidence +
                FUSION_VLM_WEIGHT * judgment.overall_score
            )
            final_confidence = fused

            # VLM veto check
            vlm_denies = (
                not judgment.same_person or
                not judgment.is_live or
                not judgment.is_authentic
            )
            veto_conf = 1.0 - judgment.overall_score

            if vlm_denies and veto_conf >= VLM_VETO_CONFIDENCE:
                final_decision = "DENY"
                vlm_override = True
                vlm_reasoning = (
                    f"⚠️ VLM OVERRIDE: Traditional pipeline granted access, "
                    f"but VLM analysis raised critical concerns "
                    f"(deny confidence: {veto_conf:.1%}).\n\n"
                    f"🧠 VLM Analysis: {judgment.reasoning}"
                )
                if judgment.red_flags:
                    vlm_reasoning += f"\n\n🚩 Red Flags: {', '.join(judgment.red_flags)}"
            else:
                vlm_reasoning = (
                    f"✅ Authentication verified by both traditional pipeline "
                    f"({trad_result.confidence:.1%}) and VLM reasoning "
                    f"({judgment.overall_score:.1%}).\n\n"
                    f"🧠 VLM Analysis: {judgment.reasoning}"
                )

            logger.info(
                f"VLM judgment: same={judgment.same_person}, "
                f"live={judgment.is_live}, authentic={judgment.is_authentic}, "
                f"overall={judgment.overall_score:.2f}, time={judgment.inference_time_ms:.0f}ms"
            )

        except Exception as e:
            logger.error(f"VLM reasoning failed: {e}", exc_info=True)
            vlm_reasoning = (
                f"✅ Traditional pipeline granted access ({trad_result.confidence:.1%}). "
                f"VLM analysis encountered an error: {str(e)[:200]}"
            )
    elif not has_refs:
        vlm_reasoning = (
            f"✅ Traditional pipeline granted access ({trad_result.confidence:.1%}). "
            f"VLM analysis skipped: no reference frames found. "
            f"Please re-register using the VLM Register page."
        )
    else:
        vlm_reasoning = (
            f"✅ Traditional pipeline granted access ({trad_result.confidence:.1%}). "
            f"VLM analysis skipped: could not extract auth frames from video."
        )

    total_ms = (time.perf_counter() - t_start) * 1000

    # Log to audit table
    _log_auth(
        db, request, user, trad_result, final_decision,
        "vlm_override" if vlm_override else None
    )

    # Build response
    response = {
        "authenticated": final_decision == "GRANT",
        "confidence": round(final_confidence, 4),
        "vlm_reasoning": vlm_reasoning,
        "vlm_model_used": vlm_model,
        "vlm_invoked": vlm_invoked,
        "vlm_override": vlm_override,
        "has_vlm_refs": has_refs,
        "scores": {
            "traditional": trad_scores,
            "vlm": vlm_scores,
        },
        "threat_flags": trad_result.threat_flags,
        "processing_time_ms": round(total_ms, 1),
        "traditional_decision": trad_result.decision,
        "traditional_confidence": round(trad_result.confidence, 4),
    }

    if final_decision == "GRANT":
        response["jwt_token"] = create_jwt(str(user.id), user.username)
    else:
        response["denial_reason"] = (
            "vlm_override" if vlm_override else trad_result.denial_reason
        )

    return response


# ═══════════════════════════════════════════════════════════════════════════
# VLM STATUS
# ═══════════════════════════════════════════════════════════════════════════

@vlm_router.get("/status")
async def vlm_status():
    """
    Check VLM model status.

    Returns model info, hardware details, and readiness state.
    """
    try:
        vlm = _get_vlm_reasoner()
        status = vlm.get_status()

        from app.vlm_config import detect_available_hardware
        hw = detect_available_hardware()

        return {
            "vlm": status,
            "hardware": hw,
            "endpoints": {
                "register": "/api/v1/vlm/register",
                "authenticate": "/api/v1/vlm/authenticate",
                "status": "/api/v1/vlm/status",
            },
        }
    except Exception as e:
        logger.error(f"VLM status error: {e}", exc_info=True)
        return {
            "vlm": {"loaded": False, "error": str(e)},
            "hardware": {},
        }


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _extract_frames_from_video(video_bytes: bytes, count: int = 3) -> list:
    """Extract evenly spaced frames from video bytes."""
    import tempfile, os, uuid

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
        return frames

    except Exception as e:
        logger.error(f"Frame extraction failed: {e}")
        return []
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _log_auth(db, request, user, trad_result, decision, denial_override):
    """Log authentication attempt to audit table."""
    client_ip = request.client.host if request.client else "unknown"
    try:
        crud.log_auth_attempt(
            db=db,
            user_id=user.id,
            ip_address=client_ip,
            liveness_score=trad_result.scores.liveness_score,
            deepfake_score=trad_result.scores.deepfake_score,
            similarity_score=trad_result.scores.similarity_score,
            injection_confidence=trad_result.scores.injection_confidence,
            threat_flags=trad_result.threat_flags,
            decision=decision,
            denial_reason=denial_override or trad_result.denial_reason,
        )
    except Exception as e:
        logger.error(f"Failed to log auth attempt: {e}")
