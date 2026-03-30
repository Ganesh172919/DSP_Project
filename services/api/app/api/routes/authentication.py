"""Authentication routes — challenge-response biometric verification."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.models import AuditEvent, AuthenticationAttempt, User
from app.schemas.auth import (
    AuthenticationStartRequest,
    AuthenticationStartResponse,
    AuthenticationStateResponse,
    ChallengeResponse,
    ObservationFrame,
    StageResult,
)
from app.services.biometric_crypto import decrypt_template
from app.services.challenge_engine import select_challenges
from app.services.decision_engine import build_stage_results, compute_decision
from app.services.feature_extractor import compare_template, extract_geometry_metrics
from app.services.liveness import evaluate_sequence
from app.services.risk import analyze_frame_risk

router = APIRouter(prefix="/authentication", tags=["authentication"])

MAX_ATTEMPTS = 3
LOCKOUT_MINUTES = 15


@router.post("/start", response_model=AuthenticationStartResponse)
async def start_authentication(
    body: AuthenticationStartRequest,
    session: AsyncSession = Depends(get_db_session),
):
    user = (await session.scalars(select(User).where(User.email == body.email))).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email")
    if not user.registration_completed:
        raise HTTPException(status_code=400, detail="Registration not completed. Please complete enrollment first.")

    # Account lockout check
    if user.locked_until and datetime.now(timezone.utc) < user.locked_until:
        remaining = (user.locked_until - datetime.now(timezone.utc)).seconds // 60
        raise HTTPException(
            status_code=423,
            detail=f"Account temporarily locked due to {MAX_ATTEMPTS} failed attempts. Try again in {remaining + 1} minutes."
        )

    # Reset lockout if expired
    if user.locked_until and datetime.now(timezone.utc) >= user.locked_until:
        user.locked_until = None
        user.failed_consecutive_attempts = 0

    # Determine attempt number
    attempt_number = (user.failed_consecutive_attempts or 0) + 1

    challenges = select_challenges(
        security_level=body.security_level,
        accessibility_profile=user.accessibility_profile,
    )

    attempt = AuthenticationAttempt(
        user_id=user.id,
        challenges=challenges,
        security_level=body.security_level,
        attempt_number=attempt_number,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    session.add(attempt)

    session.add(AuditEvent(
        event_type="authentication_started",
        severity="info",
        user_id=user.id,
        attempt_id=attempt.id,
        message=f"Authentication attempt #{attempt_number} started (level: {body.security_level})",
    ))

    await session.commit()

    return AuthenticationStartResponse(
        attempt_id=attempt.id,
        challenges=[ChallengeResponse(**c) for c in challenges],
        attempt_number=attempt_number,
        max_attempts=MAX_ATTEMPTS,
    )


@router.post("/{attempt_id}/frame", response_model=AuthenticationStateResponse)
async def submit_authentication_frame(
    attempt_id: str,
    body: ObservationFrame,
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()

    attempt = (await session.scalars(
        select(AuthenticationAttempt).where(AuthenticationAttempt.id == attempt_id)
    )).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Authentication attempt not found")
    if attempt.status != "active":
        raise HTTPException(status_code=410, detail="Attempt already completed")
    if datetime.now(timezone.utc) > attempt.expires_at:
        attempt.status = "expired"
        await session.commit()
        raise HTTPException(status_code=410, detail="Authentication attempt expired")

    user = (await session.scalars(select(User).where(User.id == attempt.user_id))).first()
    if not user or not user.biometric_template:
        raise HTTPException(status_code=404, detail="User template not found")

    # Decrypt template
    template_data = decrypt_template(user.biometric_template, settings.biometric_master_key, user.id)
    template = json.loads(template_data.decode())

    # Risk analysis
    t0 = time.monotonic()
    risk = analyze_frame_risk(
        frame_b64=body.frame_b64,
        landmarks=body.landmarks,
        client_metrics=body.client_metrics,
    )

    # Feature comparison
    recognition_score, feature_score, matching_anomalies = compare_template(
        template, body.landmarks, body.client_metrics
    )

    # Store observation
    observations = attempt.observations or []
    observations.append({
        "step": body.step,
        "challenge_id": body.challenge_id,
        "landmarks": body.landmarks,
        "client_metrics": body.client_metrics,
        "risk": {
            "pad_score": risk.get("pad_score", 0.65),
            "deepfake_score": risk.get("deepfake_score", 0.65),
            "quality_score": risk.get("quality_score", 55.0),
        },
        "recognition_score": recognition_score,
        "feature_score": feature_score,
        "captured_at": body.captured_at.isoformat(),
    })
    attempt.observations = observations

    # Update latency tracking
    latencies = attempt.stage_latencies or {}
    latencies[f"frame_{len(observations)}"] = round((time.monotonic() - t0) * 1000, 1)
    attempt.stage_latencies = latencies

    await session.commit()

    # Build interim stage results
    face_present = 1.0 if body.client_metrics.get("face_present") else 0.0
    stage_results = build_stage_results(
        face_score=face_present,
        pad_score=risk.get("pad_score", 0.65),
        recognition_score=recognition_score,
        feature_score=feature_score,
        liveness_score=0.5,  # Provisional until sequence complete
        deepfake_score=risk.get("deepfake_score", 0.65),
    )

    attempts_remaining = MAX_ATTEMPTS - (attempt.attempt_number or 1)

    return AuthenticationStateResponse(
        attempt_id=attempt.id,
        stage_results=[StageResult(**r) for r in stage_results],
        anomalies=matching_anomalies + risk.get("anomalies", []),
        attempts_remaining=max(0, attempts_remaining),
    )


@router.post("/{attempt_id}/complete", response_model=AuthenticationStateResponse)
async def complete_authentication(
    attempt_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()

    attempt = (await session.scalars(
        select(AuthenticationAttempt).where(AuthenticationAttempt.id == attempt_id)
    )).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Authentication attempt not found")
    if attempt.status != "active":
        raise HTTPException(status_code=410, detail="Attempt already completed")

    user = (await session.scalars(select(User).where(User.id == attempt.user_id))).first()
    if not user or not user.biometric_template:
        raise HTTPException(status_code=404, detail="User template not found")

    template_data = decrypt_template(user.biometric_template, settings.biometric_master_key, user.id)
    template = json.loads(template_data.decode())

    observations = attempt.observations or []
    challenges = attempt.challenges or []

    # Aggregate risk scores across all frames
    pad_scores = [o.get("risk", {}).get("pad_score", 0.65) for o in observations]
    deepfake_scores = [o.get("risk", {}).get("deepfake_score", 0.65) for o in observations]
    recognition_scores = [o.get("recognition_score", 0.0) for o in observations]
    feature_scores = [o.get("feature_score", 0.0) for o in observations]

    avg_pad = sum(pad_scores) / max(len(pad_scores), 1)
    avg_deepfake = sum(deepfake_scores) / max(len(deepfake_scores), 1)
    max_recognition = max(recognition_scores, default=0.0)
    max_feature = max(feature_scores, default=0.0)

    # Liveness evaluation
    liveness_score, liveness_anomalies, liveness_results = evaluate_sequence(challenges, observations)

    # Face presence
    face_present_ratio = sum(
        1 for o in observations if o.get("client_metrics", {}).get("face_present")
    ) / max(len(observations), 1)

    # Build final stage results
    stage_results = build_stage_results(
        face_score=face_present_ratio,
        pad_score=avg_pad,
        recognition_score=max_recognition,
        feature_score=max_feature,
        liveness_score=liveness_score,
        deepfake_score=avg_deepfake,
    )

    all_anomalies = liveness_anomalies
    for o in observations:
        risk_data = o.get("risk", {})
        if isinstance(risk_data, dict):
            all_anomalies.extend(
                a for a in risk_data.get("anomalies", []) if isinstance(a, str) and a not in all_anomalies
            )

    # Context for decision engine
    context = {
        "device_known": True,
        "consecutive_failures": user.failed_consecutive_attempts or 0,
    }

    decision = compute_decision(stage_results, all_anomalies, context)

    # Update attempt
    attempt.status = "approved" if decision["authenticated"] else "denied"
    attempt.final_score = decision["final_score"]
    attempt.stage_results = stage_results
    attempt.anomalies = decision["anomalies"]
    attempt.denial_reasons = decision.get("reasoning", {}).get("denial_reasons", [])
    attempt.needs_review = decision.get("needs_review", False)
    attempt.completed_at = datetime.now(timezone.utc)

    # Update user lockout tracking
    if decision["authenticated"]:
        user.failed_consecutive_attempts = 0
        user.locked_until = None
        user.last_authenticated_at = datetime.now(timezone.utc)
        severity = "info"
    else:
        user.failed_consecutive_attempts = (user.failed_consecutive_attempts or 0) + 1
        if user.failed_consecutive_attempts >= MAX_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
            severity = "critical"
            all_anomalies.append(
                f"Account locked for {LOCKOUT_MINUTES} minutes after {MAX_ATTEMPTS} failed attempts"
            )
        else:
            severity = "warning"

    # Audit event
    session.add(AuditEvent(
        event_type="authentication_completed",
        severity=severity,
        user_id=user.id,
        attempt_id=attempt.id,
        message=(
            f"Authentication {'approved' if decision['authenticated'] else 'denied'} "
            f"(score: {decision['final_score']:.4f}). "
            f"Anomalies: {len(decision['anomalies'])}"
        ),
        metadata_json={
            "final_score": decision["final_score"],
            "authenticated": decision["authenticated"],
            "needs_review": decision.get("needs_review", False),
            "stage_scores": {r["stage"]: r["score"] for r in stage_results},
        },
    ))

    await session.commit()

    attempts_remaining = max(0, MAX_ATTEMPTS - (user.failed_consecutive_attempts or 0))

    return AuthenticationStateResponse(
        attempt_id=attempt.id,
        stage_results=[StageResult(**r) for r in stage_results],
        final_score=decision["final_score"],
        authenticated=decision["authenticated"],
        anomalies=decision["anomalies"],
        needs_review=decision.get("needs_review", False),
        attempts_remaining=attempts_remaining,
    )
