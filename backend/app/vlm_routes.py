"""
vlm_routes.py — FastAPI router for VLM-enhanced authentication endpoints.

This module is ADDITIVE — it does not modify existing routes.
All VLM endpoints are mounted under /api/v1/vlm/.

Endpoints:
  POST /api/v1/vlm/register      — Video-based registration with VLM reference frames
  POST /api/v1/vlm/authenticate   — VLM-enhanced video authentication
  GET  /api/v1/vlm/status         — VLM model status
"""

import logging
from typing import Optional, List

import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import RATE_LIMIT
from app.db.models import get_db
from app.db import crud
from app.db.vlm_crud import (
    store_vlm_reference_frames,
    get_vlm_reference_frames,
    has_vlm_reference_frames,
)
from app.crypto import encrypt_embedding, decrypt_embedding, create_jwt
from app.vlm_pipeline import VLMAuthPipeline

logger = logging.getLogger(__name__)

# ─── Router ─────────────────────────────────────────────────────────────────
vlm_router = APIRouter(prefix="/api/v1/vlm", tags=["VLM Authentication"])

# Rate limiter (shares limiter with main app)
limiter = Limiter(key_func=get_remote_address)

# ─── VLM Pipeline (lazy init) ──────────────────────────────────────────────
_vlm_pipeline: Optional[VLMAuthPipeline] = None


def get_vlm_pipeline() -> VLMAuthPipeline:
    """Get or initialize the VLM pipeline (lazy singleton)."""
    global _vlm_pipeline
    if _vlm_pipeline is None:
        logger.info("Initializing VLM pipeline (lazy)...")
        _vlm_pipeline = VLMAuthPipeline()
        logger.info("VLM pipeline initialized")
    return _vlm_pipeline


# ═══════════════════════════════════════════════════════════════════════════
# VLM REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════

@vlm_router.post("/register")
async def vlm_register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Register a user with video-based capture and VLM reference frames.

    Accepts:
      - username: unique username
      - email: unique email
      - video: 5-second webcam video (WebM/MP4)

    Pipeline:
      1. Decode video → extract frames
      2. Run existing registration (face detection, embedding extraction)
      3. Select 3 best frames as VLM reference frames
      4. Store encrypted embedding + encrypted reference frames

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

    # Read video bytes
    video_bytes = await video.read()
    if not video_bytes:
        raise HTTPException(status_code=400, detail="Empty video file")

    logger.info(f"VLM registration: received video ({len(video_bytes)} bytes) for user '{username}'")

    try:
        vlm_pipe = get_vlm_pipeline()

        # Run video-based registration
        template, liveness_score, face_quality, ref_frames, ref_qualities = (
            vlm_pipe.register_face_from_video(video_bytes)
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

        # Store VLM reference frames (new table)
        vlm_records = store_vlm_reference_frames(
            db=db,
            user_id=user.id,
            frames=ref_frames,
            qualities=ref_qualities,
        )

        logger.info(
            f"VLM registered user '{username}' (id={user.id}): "
            f"{len(vlm_records)} ref frames stored"
        )

        return {
            "user_id": user.id,
            "username": username,
            "liveness_score": round(liveness_score, 4),
            "face_quality": round(face_quality, 4),
            "vlm_ref_frames_stored": len(vlm_records),
            "status": "registered",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"VLM registration failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="VLM registration failed — see server logs"
        )


# ═══════════════════════════════════════════════════════════════════════════
# VLM AUTHENTICATION
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

    Accepts:
      - username: registered username
      - video: 5-second webcam video (WebM/MP4)

    Pipeline:
      1. Run traditional video authentication (all existing layers)
      2. If traditional says DENY → return immediately
      3. If traditional says GRANT → VLM Judge reviews registration vs auth frames
      4. Fuse scores: final = 0.6 × traditional + 0.4 × VLM
      5. VLM can veto a GRANT with high confidence denial
      6. Return combined result with VLM natural language reasoning

    Returns:
      {
        authenticated, confidence, vlm_reasoning, vlm_model_used,
        scores: {traditional, vlm_identity, vlm_liveness, vlm_authenticity, vlm_overall},
        threat_flags, processing_time_ms, jwt_token or denial_reason
      }
    """
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

    # Get VLM reference frames (may be empty for users registered without VLM)
    ref_frames = get_vlm_reference_frames(db, user.id)

    has_vlm_refs = len(ref_frames) > 0
    logger.info(
        f"VLM auth for '{username}': "
        f"video={len(video_bytes)} bytes, "
        f"has_vlm_refs={has_vlm_refs} ({len(ref_frames)} frames)"
    )

    # Run VLM hybrid pipeline
    vlm_pipe = get_vlm_pipeline()
    result = vlm_pipe.authenticate_vlm(
        stored_embedding=stored_embedding,
        video_bytes=video_bytes,
        ref_frames=ref_frames,
    )

    # Get client IP for audit logging
    client_ip = request.client.host if request.client else "unknown"

    # Log to audit table (using traditional result details)
    trad = result.traditional_result
    crud.log_auth_attempt(
        db=db,
        user_id=user.id,
        ip_address=client_ip,
        liveness_score=trad.scores.liveness_score if trad else None,
        deepfake_score=trad.scores.deepfake_score if trad else None,
        similarity_score=trad.scores.similarity_score if trad else None,
        injection_confidence=trad.scores.injection_confidence if trad else None,
        threat_flags=trad.threat_flags if trad else [],
        decision=result.final_decision,
        denial_reason=trad.denial_reason if trad and trad.decision == "DENY" else (
            "vlm_override" if result.vlm_override else None
        ),
    )

    # Build response
    trad_scores = {}
    if trad:
        trad_scores = {
            "liveness": trad.scores.liveness_score,
            "deepfake": trad.scores.deepfake_score,
            "similarity": trad.scores.similarity_score,
            "injection": trad.scores.injection_confidence,
        }

    vlm_scores = {}
    if result.vlm_judgment:
        j = result.vlm_judgment
        vlm_scores = {
            "vlm_identity": j.same_person_confidence,
            "vlm_liveness": j.liveness_confidence,
            "vlm_authenticity": j.authenticity_confidence,
            "vlm_overall": j.overall_score,
        }

    response = {
        "authenticated": result.final_decision == "GRANT",
        "confidence": round(result.final_confidence, 4),
        "vlm_reasoning": result.vlm_reasoning,
        "vlm_model_used": result.vlm_model_used,
        "vlm_invoked": result.vlm_invoked,
        "vlm_override": result.vlm_override,
        "has_vlm_refs": has_vlm_refs,
        "scores": {
            "traditional": trad_scores,
            "vlm": vlm_scores,
        },
        "threat_flags": trad.threat_flags if trad else [],
        "processing_time_ms": round(result.total_processing_time_ms, 1),
        "traditional_decision": trad.decision if trad else None,
        "traditional_confidence": round(trad.confidence, 4) if trad else None,
    }

    if result.final_decision == "GRANT":
        response["jwt_token"] = create_jwt(str(user.id), user.username)
    else:
        response["denial_reason"] = (
            "vlm_override" if result.vlm_override
            else (trad.denial_reason if trad else "unknown")
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
        vlm_pipe = get_vlm_pipeline()
        status = vlm_pipe.get_vlm_status()

        # Also get hardware info
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
            "endpoints": {
                "register": "/api/v1/vlm/register",
                "authenticate": "/api/v1/vlm/authenticate",
                "status": "/api/v1/vlm/status",
            },
        }
