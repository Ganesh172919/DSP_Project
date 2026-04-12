"""
vlm_routes.py - FastAPI router for VLM-enhanced authentication endpoints.

These routes are additive and keep the traditional authentication flow intact.

Endpoints:
  POST /api/v1/vlm/register
  POST /api/v1/vlm/authenticate
  POST /api/v1/vlm/authenticate/pure
  GET  /api/v1/vlm/status
  POST /api/v1/vlm/warmup
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.crypto import create_jwt, decrypt_embedding, encrypt_embedding
from app.db import crud
from app.db.models import get_db
from app.db.vlm_crud import (
    get_vlm_reference_frames,
    has_vlm_reference_frames,
    store_vlm_reference_frames,
)
from app.video_utils import extract_evenly_spaced_frames, infer_video_suffix
from app.vlm_config import (
    FUSION_TRADITIONAL_WEIGHT,
    FUSION_VLM_WEIGHT,
    VLM_AUTH_FRAME_COUNT,
    VLM_FORCE_DENY_RED_FLAGS,
    VLM_VETO_CONFIDENCE,
    detect_available_hardware,
)

logger = logging.getLogger(__name__)

vlm_router = APIRouter(prefix="/api/v1/vlm", tags=["VLM Authentication"])

_base_pipeline = None
_vlm_reasoner = None
_vlm_auth_pipeline = None


def _get_base_pipeline():
    """Get the existing traditional AuthPipeline instance."""
    global _base_pipeline
    if _base_pipeline is None:
        try:
            from app import main as app_main

            if getattr(app_main, "pipeline", None) is not None:
                _base_pipeline = app_main.pipeline
                return _base_pipeline
        except Exception:
            pass

        from app.pipeline import AuthPipeline

        _base_pipeline = AuthPipeline()
    return _base_pipeline


def _get_vlm_reasoner():
    """Get the lazy VLM reasoner."""
    global _vlm_reasoner
    if _vlm_reasoner is None:
        from app.models.vlm_reasoner import VLMReasoner

        _vlm_reasoner = VLMReasoner()
    return _vlm_reasoner


def _get_vlm_auth_pipeline():
    """Get the pure VLM authentication pipeline."""
    global _vlm_auth_pipeline
    if _vlm_auth_pipeline is None:
        from app.vlm_pipeline import VLMAuthPipeline

        _vlm_auth_pipeline = VLMAuthPipeline()
    _vlm_auth_pipeline._vlm = _get_vlm_reasoner()
    return _vlm_auth_pipeline


async def _read_uploaded_frames(
    frame_files: Optional[List[UploadFile]],
) -> list[np.ndarray]:
    """Decode uploaded JPEG/PNG auth frames, if any were provided."""
    frames: list[np.ndarray] = []
    for upload in frame_files or []:
        content = await upload.read()
        if not content:
            continue

        image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is not None:
            frames.append(image)

    return frames


def _build_vlm_scores(judgment) -> dict:
    """Normalize VLM scores into a stable response payload."""
    return {
        "vlm_identity": judgment.same_person_confidence,
        "vlm_liveness": judgment.liveness_confidence,
        "vlm_authenticity": judgment.authenticity_confidence,
        "vlm_overall": judgment.overall_score,
    }


def _format_vlm_reasoning(reasoning: str, red_flags: list[str]) -> str:
    """Append red flags to the reasoning text when available."""
    reasoning = (reasoning or "").strip()
    if red_flags:
        flags_text = ", ".join(red_flags)
        if reasoning:
            return f"{reasoning}\n\nRed flags: {flags_text}"
        return f"Red flags: {flags_text}"
    return reasoning


def _log_hybrid_auth(db, request, user, trad_result, decision: str, denial_reason: Optional[str]):
    """Log a hybrid auth attempt using the traditional pipeline scores."""
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
            denial_reason=denial_reason,
        )
    except Exception as exc:
        logger.error("Failed to log hybrid auth attempt: %s", exc)


def _log_pure_vlm_auth(db, request, user, result):
    """Log a pure VLM auth attempt into the existing audit table."""
    client_ip = request.client.host if request.client else "unknown"
    denial_reason = result.error or (None if result.decision == "GRANT" else "vlm_denied")
    try:
        crud.log_auth_attempt(
            db=db,
            user_id=user.id,
            ip_address=client_ip,
            liveness_score=result.liveness_confidence,
            deepfake_score=max(0.0, 1.0 - result.authenticity_confidence),
            similarity_score=result.same_person_confidence,
            injection_confidence=None,
            threat_flags=list(result.red_flags),
            decision=result.decision,
            denial_reason=denial_reason,
        )
    except Exception as exc:
        logger.error("Failed to log pure VLM auth attempt: %s", exc)


@vlm_router.post("/register")
async def vlm_register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    face_data: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Register a user with the traditional face template and VLM reference frames.
    """
    existing = crud.get_user_by_username(db, username)
    if existing:
        raise HTTPException(status_code=409, detail=f"Username '{username}' already registered")

    existing_email = crud.get_user_by_email(db, email)
    if existing_email:
        raise HTTPException(status_code=409, detail=f"Email '{email}' already registered")

    frames = await _read_uploaded_frames(face_data)
    if not frames:
        raise HTTPException(status_code=400, detail="No valid images uploaded")

    logger.info("VLM registration received %s frames for '%s'", len(frames), username)

    try:
        pipe = _get_base_pipeline()
        template, liveness_score, face_quality = pipe.register_face(
            frames,
            skip_injection_check=True,
        )

        encrypted = encrypt_embedding(template)
        user = crud.create_user(
            db=db,
            username=username,
            email=email,
            embedding_enc=encrypted,
            face_quality=face_quality,
        )

        qualities = [face_quality] * len(frames)
        stored_count = store_vlm_reference_frames(
            db=db,
            user_id=user.id,
            frames=frames,
            qualities=qualities,
        )

        return {
            "user_id": user.id,
            "username": username,
            "liveness_score": round(liveness_score, 4),
            "face_quality": round(face_quality, 4),
            "vlm_ref_frames_stored": stored_count,
            "status": "registered",
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("VLM registration failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"VLM registration failed: {exc}")


@vlm_router.post("/authenticate")
async def vlm_authenticate(
    request: Request,
    username: str = Form(...),
    video: UploadFile = File(...),
    auth_frames: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
):
    """
    Hybrid authentication: traditional pipeline first, VLM judge second.
    """
    t_start = time.perf_counter()

    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    stored_embedding = decrypt_embedding(user.embedding_enc)
    video_bytes = await video.read()
    uploaded_auth_frames = await _read_uploaded_frames(auth_frames)

    if not video_bytes:
        raise HTTPException(status_code=400, detail="Empty video file")

    logger.info(
        "Hybrid VLM auth for '%s': video_bytes=%s, uploaded_frames=%s",
        username,
        len(video_bytes),
        len(uploaded_auth_frames),
    )

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

    has_refs = has_vlm_reference_frames(db, user.id)

    if trad_result.decision == "DENY":
        total_ms = (time.perf_counter() - t_start) * 1000
        _log_hybrid_auth(db, request, user, trad_result, "DENY", trad_result.denial_reason)
        return {
            "authenticated": False,
            "confidence": round(trad_result.confidence, 4),
            "vlm_reasoning": (
                f"Traditional pipeline denied authentication: {trad_result.denial_reason}. "
                "VLM analysis was skipped."
            ),
            "vlm_model_used": "none",
            "vlm_invoked": False,
            "vlm_override": False,
            "vlm_red_flags": [],
            "has_vlm_refs": has_refs,
            "scores": {"traditional": trad_scores, "vlm": {}},
            "threat_flags": trad_result.threat_flags,
            "processing_time_ms": round(total_ms, 1),
            "traditional_decision": "DENY",
            "traditional_confidence": round(trad_result.confidence, 4),
            "denial_reason": trad_result.denial_reason,
            "auth_frames_used": len(uploaded_auth_frames),
        }

    ref_frames = get_vlm_reference_frames(db, user.id)
    vlm_auth_frames = list(uploaded_auth_frames)

    if not vlm_auth_frames and video_bytes:
        suffix = infer_video_suffix(video.filename, video.content_type, default=".webm")
        vlm_auth_frames = extract_evenly_spaced_frames(
            video_bytes,
            count=VLM_AUTH_FRAME_COUNT,
            suffix=suffix,
        )

    final_decision = "GRANT"
    final_confidence = trad_result.confidence
    vlm_reasoning = ""
    vlm_scores = {}
    vlm_invoked = False
    vlm_override = False
    vlm_model = "none"
    vlm_red_flags: list[str] = []

    if ref_frames and vlm_auth_frames:
        try:
            judgment = _get_vlm_reasoner().judge_authentication(ref_frames, vlm_auth_frames)
            vlm_invoked = True
            vlm_model = judgment.model_used
            vlm_red_flags = list(judgment.red_flags)
            vlm_scores = _build_vlm_scores(judgment)

            final_confidence = (
                FUSION_TRADITIONAL_WEIGHT * trad_result.confidence
                + FUSION_VLM_WEIGHT * judgment.overall_score
            )

            force_deny_from_flags = any(
                flag in set(judgment.red_flags)
                for flag in VLM_FORCE_DENY_RED_FLAGS
            )
            vlm_denies = (
                not judgment.same_person
                or not judgment.is_live
                or not judgment.is_authentic
            )
            veto_confidence = 1.0 - judgment.overall_score

            if force_deny_from_flags:
                final_decision = "DENY"
                vlm_override = True
            elif vlm_denies and veto_confidence >= VLM_VETO_CONFIDENCE:
                final_decision = "DENY"
                vlm_override = True

            vlm_reasoning = _format_vlm_reasoning(judgment.reasoning, judgment.red_flags)
            if not vlm_reasoning:
                vlm_reasoning = "VLM analysis completed without additional commentary."

        except Exception as exc:
            logger.error("VLM reasoning failed: %s", exc, exc_info=True)
            vlm_reasoning = (
                f"Traditional pipeline granted access ({trad_result.confidence:.1%}). "
                f"VLM analysis encountered an error: {str(exc)[:200]}"
            )
    elif not ref_frames:
        vlm_reasoning = (
            f"Traditional pipeline granted access ({trad_result.confidence:.1%}). "
            "VLM analysis skipped because this user has no VLM registration frames. "
            "Please re-register with the VLM Register page."
        )
    else:
        vlm_reasoning = (
            f"Traditional pipeline granted access ({trad_result.confidence:.1%}). "
            "VLM analysis skipped because no authentication frames could be extracted."
        )

    total_ms = (time.perf_counter() - t_start) * 1000
    denial_reason = "vlm_override" if final_decision == "DENY" and vlm_override else trad_result.denial_reason
    _log_hybrid_auth(db, request, user, trad_result, final_decision, denial_reason)

    response = {
        "authenticated": final_decision == "GRANT",
        "confidence": round(final_confidence, 4),
        "vlm_reasoning": vlm_reasoning,
        "vlm_model_used": vlm_model,
        "vlm_invoked": vlm_invoked,
        "vlm_override": vlm_override,
        "vlm_red_flags": vlm_red_flags,
        "has_vlm_refs": bool(ref_frames),
        "scores": {
            "traditional": trad_scores,
            "vlm": vlm_scores,
        },
        "threat_flags": trad_result.threat_flags,
        "processing_time_ms": round(total_ms, 1),
        "traditional_decision": trad_result.decision,
        "traditional_confidence": round(trad_result.confidence, 4),
        "auth_frames_used": len(vlm_auth_frames),
    }

    if final_decision == "GRANT":
        response["jwt_token"] = create_jwt(str(user.id), user.username)
    else:
        response["denial_reason"] = "vlm_override" if vlm_override else trad_result.denial_reason

    return response


@vlm_router.post("/authenticate/pure")
async def vlm_authenticate_pure(
    request: Request,
    username: str = Form(...),
    video: UploadFile = File(...),
    auth_frames: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
):
    """
    Pure VLM authentication with no traditional pipeline involvement.

    This reuses the VLM registration reference frames stored on disk.
    """
    t_start = time.perf_counter()

    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    ref_frames = get_vlm_reference_frames(db, user.id)
    if not ref_frames:
        raise HTTPException(
            status_code=400,
            detail=(
                "No VLM reference frames found for this user. "
                "Please register with the VLM Register page first."
            ),
        )

    video_bytes = await video.read()
    uploaded_auth_frames = await _read_uploaded_frames(auth_frames)
    auth_frame_count = len(uploaded_auth_frames)

    if not uploaded_auth_frames:
        if not video_bytes:
            raise HTTPException(status_code=400, detail="Empty video file")

        suffix = infer_video_suffix(video.filename, video.content_type, default=".webm")
        uploaded_auth_frames = extract_evenly_spaced_frames(
            video_bytes,
            count=VLM_AUTH_FRAME_COUNT,
            suffix=suffix,
        )
        auth_frame_count = len(uploaded_auth_frames)

    if not uploaded_auth_frames:
        raise HTTPException(
            status_code=400,
            detail="Could not extract authentication frames from the provided video",
        )

    result = _get_vlm_auth_pipeline().authenticate(ref_frames, uploaded_auth_frames)
    total_ms = (time.perf_counter() - t_start) * 1000
    _log_pure_vlm_auth(db, request, user, result)

    response = {
        "authenticated": result.decision == "GRANT",
        "decision": result.decision,
        "confidence": round(result.confidence, 4),
        "vlm_reasoning": _format_vlm_reasoning(result.reasoning, result.red_flags),
        "vlm_model_used": result.model_used,
        "vlm_red_flags": list(result.red_flags),
        "scores": {
            "vlm_identity": result.same_person_confidence,
            "vlm_liveness": result.liveness_confidence,
            "vlm_authenticity": result.authenticity_confidence,
            "vlm_overall": result.confidence,
        },
        "same_person": result.same_person,
        "is_live": result.is_live,
        "is_authentic": result.is_authentic,
        "has_vlm_refs": True,
        "processing_time_ms": round(total_ms, 1),
        "auth_frames_used": auth_frame_count,
    }

    if result.decision == "GRANT":
        response["jwt_token"] = create_jwt(str(user.id), user.username)
    else:
        response["denial_reason"] = result.error or "vlm_denied"

    return response


@vlm_router.get("/status")
async def vlm_status():
    """Return VLM hardware and model readiness information."""
    reasoner = _get_vlm_reasoner()
    return {
        "vlm": reasoner.get_status(),
        "hardware": detect_available_hardware(),
        "endpoints": {
            "register": "/api/v1/vlm/register",
            "authenticate": "/api/v1/vlm/authenticate",
            "authenticate_pure": "/api/v1/vlm/authenticate/pure",
            "warmup": "/api/v1/vlm/warmup",
            "status": "/api/v1/vlm/status",
        },
    }


@vlm_router.post("/warmup")
async def vlm_warmup():
    """Trigger lazy model download/load ahead of the first auth request."""
    reasoner = _get_vlm_reasoner()
    status = reasoner.ensure_loaded()
    return {
        "ready": bool(status.get("loaded")),
        "vlm": status,
        "hardware": detect_available_hardware(),
    }
