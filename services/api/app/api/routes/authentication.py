"""Authentication routes — challenge-response biometric verification."""

from __future__ import annotations
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models import AuditEvent, AuthenticationAttempt, User
from app.schemas.auth import (
    AuthenticationStartRequest,
    AuthenticationStartResponse,
    AuthenticationStateResponse,
    ChallengeResponse,
    LiveChallengeTelemetry,
    LiveProcessingTelemetry,
    ObservationFrame,
    StageResult,
)
from app.services.biometric_crypto import decrypt_template
from app.services.challenge_engine import select_challenges
from app.services.decision_engine import build_stage_results, compute_decision
from app.services.feature_extractor import compare_template
from app.services.liveness import evaluate_challenge, evaluate_observed_challenges, evaluate_sequence
from app.services.risk import analyze_frame_risk

router = APIRouter(prefix="/authentication", tags=["authentication"])

MAX_ATTEMPTS = 3
LOCKOUT_MINUTES = 15


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalise_email(email: str) -> str:
    return email.strip().lower()


def _ordered_unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _challenge_progress(
    challenges: list[dict],
    observations: list[dict],
    active_challenge_id: str | None = None,
) -> tuple[list[LiveChallengeTelemetry], dict[str, dict]]:
    grouped: dict[str, list[dict]] = {}
    for observation in observations:
        cid = observation.get("challenge_id")
        if not cid:
            continue
        grouped.setdefault(cid, []).append(observation)

    results_by_id: dict[str, dict] = {}
    telemetry: list[LiveChallengeTelemetry] = []

    for challenge in challenges:
        cid = challenge.get("id", "")
        frames = grouped.get(cid, [])
        expected_frames = max(3, int(challenge.get("duration_seconds", 0) or 0))
        progress = min(len(frames) / max(expected_frames, 1), 1.0)
        title = str(challenge.get("title", cid))

        if frames:
            score, passed, message = evaluate_challenge(challenge, frames)
            results_by_id[cid] = {
                "score": round(score, 4),
                "passed": passed,
                "message": message,
            }
            status = "running" if cid == active_challenge_id and progress < 1.0 else "completed"
            telemetry.append(LiveChallengeTelemetry(
                id=cid,
                title=title,
                frames_processed=len(frames),
                progress=round(progress, 4),
                status=status,
                score=round(score, 4),
                passed=passed,
                message=message,
            ))
        else:
            telemetry.append(LiveChallengeTelemetry(
                id=cid,
                title=title,
                frames_processed=0,
                progress=0.0,
                status="running" if cid == active_challenge_id else "pending",
                message="Waiting for live frames",
            ))

    return telemetry, results_by_id


@router.post("/start", response_model=AuthenticationStartResponse)
async def start_authentication(
    body: AuthenticationStartRequest,
    session: AsyncSession = Depends(get_db_session),
):
    email = _normalise_email(str(body.email))
    user = (await session.scalars(select(User).where(User.email == email))).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="No account found with this email. Use the same email used during registration.",
        )
    if not user.registration_completed:
        raise HTTPException(status_code=400, detail="Registration not completed. Please complete enrollment first.")

    # Account lockout check
    if user.locked_until and datetime.now(timezone.utc) < _as_utc(user.locked_until):
        remaining = (_as_utc(user.locked_until) - datetime.now(timezone.utc)).seconds // 60
        raise HTTPException(
            status_code=423,
            detail=f"Account temporarily locked due to {MAX_ATTEMPTS} failed attempts. Try again in {remaining + 1} minutes."
        )

    # Reset lockout if expired
    if user.locked_until and datetime.now(timezone.utc) >= _as_utc(user.locked_until):
        user.locked_until = None
        user.failed_consecutive_attempts = 0

    # Determine attempt number
    attempt_number = (user.failed_consecutive_attempts or 0) + 1

    challenges = select_challenges(
        security_level=body.security_level,
        accessibility_profile=user.accessibility_profile,
        include_internal=True,
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
        challenges=[ChallengeResponse(**{
            "id": c["id"],
            "title": c["title"],
            "description": c["description"],
            "category": c["category"],
            "duration_seconds": c["duration_seconds"],
        }) for c in challenges],
        attempt_number=attempt_number,
        max_attempts=MAX_ATTEMPTS,
    )


@router.post("/{attempt_id}/frame", response_model=AuthenticationStateResponse)
async def submit_authentication_frame(
    attempt_id: str,
    body: ObservationFrame,
    session: AsyncSession = Depends(get_db_session),
):
    attempt = (await session.scalars(
        select(AuthenticationAttempt).where(AuthenticationAttempt.id == attempt_id)
    )).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Authentication attempt not found")
    if attempt.status != "active":
        raise HTTPException(status_code=410, detail="Attempt already completed")
    if datetime.now(timezone.utc) > _as_utc(attempt.expires_at):
        attempt.status = "expired"
        await session.commit()
        raise HTTPException(status_code=410, detail="Authentication attempt expired")
    challenge_lookup = {
        str(challenge.get("id")): challenge for challenge in (attempt.challenges or [])
    }
    if not body.challenge_id or body.challenge_id not in challenge_lookup:
        raise HTTPException(status_code=400, detail="Invalid or missing challenge id")

    user = (await session.scalars(select(User).where(User.id == attempt.user_id))).first()
    if not user or not user.biometric_template:
        raise HTTPException(status_code=404, detail="User template not found")

    # Decrypt template
    template = decrypt_template(user.id, user.biometric_template)

    # Risk analysis
    t0 = time.monotonic()
    risk = analyze_frame_risk(
        frame_b64=body.frame_b64,
        landmarks=body.landmarks,
        client_metrics=body.client_metrics,
    )
    guidance = _ordered_unique(risk.get("guidance", []))

    # Feature comparison
    recognition_score, feature_score, matching_anomalies = compare_template(
        template, body.landmarks, body.client_metrics
    )

    # Store observation
    observations = list(attempt.observations or [])
    observations.append({
        "step": body.step,
        "challenge_id": body.challenge_id,
        "landmarks": body.landmarks,
        "client_metrics": body.client_metrics,
        "risk": {
            "pad_score": risk.get("pad_score", 0.65),
            "deepfake_score": risk.get("deepfake_score", 0.65),
            "quality_score": risk.get("quality_score", 55.0),
            "guidance": risk.get("guidance", []),
            "anomalies": risk.get("anomalies", []),
        },
        "recognition_score": recognition_score,
        "feature_score": feature_score,
        "captured_at": body.captured_at.isoformat(),
    })
    attempt.observations = observations

    # Update latency tracking
    latencies = dict(attempt.stage_latencies or {})
    latencies[f"frame_{len(observations)}"] = round((time.monotonic() - t0) * 1000, 1)
    attempt.stage_latencies = latencies

    await session.commit()

    preview_score, preview_anomalies, _ = evaluate_observed_challenges(attempt.challenges or [], observations)
    challenge_telemetry, challenge_results = _challenge_progress(
        attempt.challenges or [],
        observations,
        active_challenge_id=body.challenge_id,
    )
    current_result = challenge_results.get(body.challenge_id or "", {})
    processed_challenges = sum(1 for item in challenge_telemetry if item.frames_processed > 0)
    frame_analysis_available = body.frame_b64 is not None and not any(
        "frame analysis unavailable" in str(anomaly).lower() for anomaly in risk.get("anomalies", [])
    )
    capture_age_ms = max(
        0.0,
        round((datetime.now(timezone.utc) - _as_utc(body.captured_at)).total_seconds() * 1000, 1),
    )

    # Build interim stage results
    face_present = 1.0 if body.client_metrics.get("face_present") else 0.0
    stage_results = build_stage_results(
        face_score=face_present,
        pad_score=risk.get("pad_score", 0.65),
        recognition_score=recognition_score,
        feature_score=feature_score,
        liveness_score=preview_score,
        deepfake_score=risk.get("deepfake_score", 0.65),
    )

    attempts_remaining = MAX_ATTEMPTS - (attempt.attempt_number or 1)
    anomalies = _ordered_unique(matching_anomalies + risk.get("anomalies", []) + preview_anomalies)

    return AuthenticationStateResponse(
        attempt_id=attempt.id,
        stage_results=[StageResult(**r) for r in stage_results],
        anomalies=anomalies,
        denial_reasons=[],
        attempts_remaining=max(0, attempts_remaining),
        live_telemetry=LiveProcessingTelemetry(
            processed_frames=len(observations),
            processed_challenges=processed_challenges,
            total_challenges=len(attempt.challenges or []),
            liveness_preview_score=preview_score,
            current_challenge_id=body.challenge_id,
            current_challenge_title=next(
                (challenge.title for challenge in challenge_telemetry if challenge.id == body.challenge_id),
                None,
            ),
            current_challenge_frames=next(
                (challenge.frames_processed for challenge in challenge_telemetry if challenge.id == body.challenge_id),
                0,
            ),
            current_challenge_progress=next(
                (challenge.progress for challenge in challenge_telemetry if challenge.id == body.challenge_id),
                0.0,
            ),
            current_challenge_score=current_result.get("score"),
            current_challenge_passed=current_result.get("passed"),
            current_challenge_message=str(current_result.get("message", "")),
            processing_time_ms=round((time.monotonic() - t0) * 1000, 1),
            capture_age_ms=capture_age_ms,
            quality_score=float(risk.get("quality_score", 0.0) or 0.0),
            pad_score=float(risk.get("pad_score", 0.0) or 0.0),
            deepfake_score=float(risk.get("deepfake_score", 0.0) or 0.0),
            frame_analysis_available=frame_analysis_available,
            provisional_risk=not frame_analysis_available,
            guidance=guidance,
            challenge_results=challenge_telemetry,
        ),
    )


@router.post("/{attempt_id}/complete", response_model=AuthenticationStateResponse)
async def complete_authentication(
    attempt_id: str,
    session: AsyncSession = Depends(get_db_session),
):
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

    template = decrypt_template(user.id, user.biometric_template)

    observations = attempt.observations or []
    challenges = attempt.challenges or []
    if not observations:
        raise HTTPException(
            status_code=400,
            detail="No live frames were captured. Start a new guided scan and follow the on-screen instructions.",
        )

    # Aggregate risk scores across all frames
    pad_scores = [o.get("risk", {}).get("pad_score", 0.65) for o in observations]
    deepfake_scores = [o.get("risk", {}).get("deepfake_score", 0.65) for o in observations]
    recognition_scores = [o.get("recognition_score", 0.0) for o in observations]
    feature_scores = [o.get("feature_score", 0.0) for o in observations]

    avg_pad = sum(pad_scores) / max(len(pad_scores), 1)
    avg_deepfake = sum(deepfake_scores) / max(len(deepfake_scores), 1)
    max_recognition = max(recognition_scores, default=0.0)
    max_feature = max(feature_scores, default=0.0)
    avg_quality = sum(
        float(o.get("risk", {}).get("quality_score", 0.0) or 0.0) for o in observations
    ) / max(len(observations), 1)

    # Liveness evaluation
    liveness_score, liveness_anomalies, _ = evaluate_sequence(challenges, observations)
    challenge_telemetry, challenge_results = _challenge_progress(challenges, observations)

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
    all_anomalies = _ordered_unique(all_anomalies)
    last_guidance = _ordered_unique([
        item
        for item in (observations[-1].get("risk", {}).get("guidance", []) if observations else [])
        if isinstance(item, str)
    ])

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
        denial_reasons=decision.get("reasoning", {}).get("denial_reasons", []),
        needs_review=decision.get("needs_review", False),
        attempts_remaining=attempts_remaining,
        live_telemetry=LiveProcessingTelemetry(
            processed_frames=len(observations),
            processed_challenges=sum(1 for item in challenge_telemetry if item.frames_processed > 0),
            total_challenges=len(challenges),
            liveness_preview_score=liveness_score,
            current_challenge_id=(observations[-1].get("challenge_id") if observations else None),
            current_challenge_title=next(
                (item.title for item in challenge_telemetry if item.id == (observations[-1].get("challenge_id") if observations else None)),
                None,
            ),
            current_challenge_frames=next(
                (item.frames_processed for item in challenge_telemetry if item.id == (observations[-1].get("challenge_id") if observations else None)),
                0,
            ),
            current_challenge_progress=next(
                (item.progress for item in challenge_telemetry if item.id == (observations[-1].get("challenge_id") if observations else None)),
                0.0,
            ),
            current_challenge_score=challenge_results.get((observations[-1].get("challenge_id") if observations else ""), {}).get("score"),
            current_challenge_passed=challenge_results.get((observations[-1].get("challenge_id") if observations else ""), {}).get("passed"),
            current_challenge_message=str(
                challenge_results.get((observations[-1].get("challenge_id") if observations else ""), {}).get("message", "")
            ),
            processing_time_ms=max(
                [float(value) for value in (attempt.stage_latencies or {}).values() if isinstance(value, (int, float))],
                default=0.0,
            ),
            capture_age_ms=None,
            quality_score=round(avg_quality, 2),
            pad_score=round(avg_pad, 4),
            deepfake_score=round(avg_deepfake, 4),
            frame_analysis_available=bool(observations),
            provisional_risk=False,
            guidance=last_guidance,
            challenge_results=challenge_telemetry,
        ),
    )
