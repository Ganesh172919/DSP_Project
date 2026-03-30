"""Registration routes — multi-angle biometric enrollment."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.models import AuditEvent, EnrollmentSession, User
from app.schemas.auth import (
    FrameAckResponse,
    ObservationFrame,
    RegistrationCompleteResponse,
    RegistrationStartRequest,
    RegistrationStartResponse,
)
from app.services.biometric_crypto import decrypt_template, encrypt_template
from app.services.feature_extractor import (
    build_template,
    compute_embedding,
    extract_geometry_metrics,
)
from app.services.risk import analyze_frame_risk

router = APIRouter(prefix="/registration", tags=["registration"])

REQUIRED_STEPS = ["front", "left", "right", "up", "down",
                  "smile", "frown", "brow_raise", "squint", "mouth_open"]


@router.post("/start", response_model=RegistrationStartResponse)
async def start_registration(
    body: RegistrationStartRequest,
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()

    # Check if user already exists
    existing = (await session.scalars(select(User).where(User.email == body.email))).first()
    if existing and existing.registration_completed:
        raise HTTPException(status_code=409, detail="Email already registered. Use the profile page to re-enroll.")

    # Create or update user
    if existing:
        user = existing
        user.full_name = body.full_name
        user.password_hash = bcrypt.hash(body.password)
        user.accessibility_profile = body.accessibility_profile
    else:
        user = User(
            email=body.email,
            full_name=body.full_name,
            password_hash=bcrypt.hash(body.password),
            accessibility_profile=body.accessibility_profile,
        )
        session.add(user)

    await session.flush()

    enrollment = EnrollmentSession(
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    session.add(enrollment)

    # Audit
    session.add(AuditEvent(
        event_type="registration_started",
        severity="info",
        user_id=user.id,
        message=f"Registration started for {body.email}",
    ))

    await session.commit()

    return RegistrationStartResponse(
        session_id=enrollment.id,
        expires_at=enrollment.expires_at,
    )


@router.post("/{session_id}/frame", response_model=FrameAckResponse)
async def submit_frame(
    session_id: str,
    body: ObservationFrame,
    session: AsyncSession = Depends(get_db_session),
):
    enrollment = (await session.scalars(
        select(EnrollmentSession).where(EnrollmentSession.id == session_id)
    )).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment session not found")
    if enrollment.status != "active":
        raise HTTPException(status_code=410, detail="Enrollment session already completed or expired")
    if datetime.now(timezone.utc) > enrollment.expires_at:
        enrollment.status = "expired"
        await session.commit()
        raise HTTPException(status_code=410, detail="Enrollment session expired")

    # Validate step
    if body.step not in REQUIRED_STEPS:
        raise HTTPException(status_code=400, detail=f"Unknown step: {body.step}. Valid steps: {REQUIRED_STEPS}")

    # Risk analysis on frame
    risk = analyze_frame_risk(
        frame_b64=body.frame_b64,
        landmarks=body.landmarks,
        client_metrics=body.client_metrics,
    )

    guidance = risk.get("guidance", [])
    quality = risk.get("quality_score", 50.0)

    # Quality gate — reject frames below threshold
    accepted = quality >= 40.0 and bool(body.client_metrics.get("face_present"))

    if not body.client_metrics.get("face_present"):
        guidance.insert(0, "No face detected — position yourself within the guide")
        accepted = False

    # Multi-face rejection
    face_count = body.client_metrics.get("face_count", 1)
    if isinstance(face_count, (int, float)) and face_count > 1:
        guidance.insert(0, "Multiple faces detected — only one person should be visible")
        accepted = False

    # PAD check during registration
    pad_score = risk.get("pad_score", 0.65)
    if pad_score < 0.45:
        guidance.insert(0, "Possible spoofing detected — use a real face in natural lighting")
        accepted = False

    if accepted:
        captures = enrollment.captures or []
        captures.append({
            "step": body.step,
            "landmarks": body.landmarks,
            "client_metrics": body.client_metrics,
            "quality_score": quality,
            "captured_at": body.captured_at.isoformat(),
        })
        enrollment.captures = captures

        quality_scores = enrollment.quality_scores or []
        quality_scores.append(quality)
        enrollment.quality_scores = quality_scores

        completed = enrollment.completed_steps or []
        if body.step not in completed:
            completed.append(body.step)
        enrollment.completed_steps = completed
        enrollment.total_frames_captured = (enrollment.total_frames_captured or 0) + 1

        await session.commit()

    steps_remaining = len([s for s in REQUIRED_STEPS if s not in (enrollment.completed_steps or [])])

    return FrameAckResponse(
        accepted=accepted,
        quality_score=round(quality, 1),
        guidance=guidance,
        step=body.step,
        steps_remaining=steps_remaining,
    )


@router.post("/{session_id}/complete", response_model=RegistrationCompleteResponse)
async def complete_registration(
    session_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()

    enrollment = (await session.scalars(
        select(EnrollmentSession).where(EnrollmentSession.id == session_id)
    )).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment session not found")
    if enrollment.status != "active":
        raise HTTPException(status_code=410, detail="Session already finalised")

    captures = enrollment.captures or []
    if len(captures) < 5:
        raise HTTPException(status_code=400, detail=f"Need at least 5 captures, got {len(captures)}")

    user = (await session.scalars(select(User).where(User.id == enrollment.user_id))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    quality = mean(enrollment.quality_scores or [50.0])
    template = build_template(captures, quality)
    encrypted, salt = encrypt_template(json.dumps(template).encode(), settings.biometric_master_key, user.id)

    user.biometric_template = encrypted
    user.biometric_salt = salt
    user.template_quality_score = quality
    user.security_score = template.get("security_score", 0.0)
    user.registration_completed = True
    user.registered_at = datetime.now(timezone.utc)
    user.re_enrollment_due_at = datetime.now(timezone.utc) + timedelta(days=365)

    enrollment.status = "completed"
    enrollment.completed_at = datetime.now(timezone.utc)

    session.add(AuditEvent(
        event_type="registration_completed",
        severity="info",
        user_id=user.id,
        message=f"Registration completed with quality {quality:.1f}, {len(captures)} captures across {len(enrollment.completed_steps or [])} steps",
    ))

    await session.commit()

    return RegistrationCompleteResponse(
        user_id=user.id,
        quality_score=round(quality, 1),
        security_score=round(template.get("security_score", 0.0), 1),
        steps_completed=len(enrollment.completed_steps or []),
        total_frames=enrollment.total_frames_captured or len(captures),
    )
