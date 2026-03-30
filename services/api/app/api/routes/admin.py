"""Admin routes — dashboard analytics and user management."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models import AuditEvent, AuthenticationAttempt, User
from app.schemas.auth import (
    AdminActionResponse,
    DashboardMetrics,
    UserListItem,
    UserListResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(session: AsyncSession = Depends(get_db_session)) -> DashboardMetrics:
    attempts = list((await session.scalars(select(AuthenticationAttempt))).all())
    events = list((await session.scalars(
        select(AuditEvent).order_by(desc(AuditEvent.created_at)).limit(20)
    )).all())

    total = len(attempts)
    approved = [a for a in attempts if a.status == "approved"]
    denied = [a for a in attempts if a.status == "denied"]
    durations = [
        (a.completed_at - a.created_at).total_seconds() * 1000
        for a in attempts
        if a.completed_at is not None
    ]

    # Challenge success rates
    challenge_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "passed": 0})
    for attempt in attempts:
        for challenge in (attempt.challenges or []):
            cid = challenge.get("id", "unknown")
            challenge_stats[cid]["total"] += 1
        if attempt.status == "approved":
            for challenge in (attempt.challenges or []):
                cid = challenge.get("id", "unknown")
                challenge_stats[cid]["passed"] += 1

    challenge_success_rates = {
        cid: round(stats["passed"] / max(stats["total"], 1), 3)
        for cid, stats in challenge_stats.items()
    }

    # Attack type counts from anomalies
    attack_types: dict[str, int] = defaultdict(int)
    for attempt in denied:
        for anomaly in (attempt.anomalies or []):
            if isinstance(anomaly, str):
                if "moiré" in anomaly.lower() or "screen" in anomaly.lower():
                    attack_types["screen_replay"] += 1
                elif "photo" in anomaly.lower() or "gamut" in anomaly.lower():
                    attack_types["printed_photo"] += 1
                elif "mask" in anomaly.lower() or "texture" in anomaly.lower():
                    attack_types["3d_mask"] += 1
                elif "deepfake" in anomaly.lower() or "synthetic" in anomaly.lower():
                    attack_types["deepfake"] += 1
                elif "liveness" in anomaly.lower():
                    attack_types["liveness_failure"] += 1
                elif "locked" in anomaly.lower():
                    attack_types["brute_force"] += 1

    return DashboardMetrics(
        total_authentications=total,
        success_rate=len(approved) / total if total else 0.0,
        blocked_attacks=len(denied),
        average_latency_ms=mean(durations) if durations else 0.0,
        active_alerts=len([e for e in events if e.severity in {"warning", "critical"}]),
        recent_events=[
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "severity": e.severity,
                "occurred_at": e.created_at.isoformat(),
                "message": e.message,
            }
            for e in events
        ],
        challenge_success_rates=challenge_success_rates,
        attack_type_counts=dict(attack_types),
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(session: AsyncSession = Depends(get_db_session)) -> UserListResponse:
    users = list((await session.scalars(select(User).order_by(desc(User.created_at)))).all())
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return UserListResponse(
        users=[
            UserListItem(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                registration_completed=u.registration_completed,
                security_score=u.security_score or 0.0,
                failed_attempts=u.failed_consecutive_attempts or 0,
                locked=bool(u.locked_until and now < u.locked_until),
                created_at=u.created_at.isoformat() if u.created_at else "",
            )
            for u in users
        ],
        total=len(users),
    )


@router.post("/users/{user_id}/re-enroll", response_model=AdminActionResponse)
async def force_re_enrollment(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> AdminActionResponse:
    user = (await session.scalars(select(User).where(User.id == user_id))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.registration_completed = False
    user.biometric_template = None
    user.biometric_salt = None
    user.template_quality_score = 0.0
    user.security_score = 0.0

    session.add(AuditEvent(
        event_type="forced_re_enrollment",
        severity="warning",
        user_id=user.id,
        message=f"Admin forced re-enrollment for {user.email}",
    ))

    await session.commit()

    return AdminActionResponse(success=True, message=f"Re-enrollment triggered for {user.email}")


@router.post("/users/{user_id}/unlock", response_model=AdminActionResponse)
async def unlock_user(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> AdminActionResponse:
    user = (await session.scalars(select(User).where(User.id == user_id))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.locked_until = None
    user.failed_consecutive_attempts = 0

    session.add(AuditEvent(
        event_type="account_unlocked",
        severity="info",
        user_id=user.id,
        message=f"Admin unlocked account for {user.email}",
    ))

    await session.commit()

    return AdminActionResponse(success=True, message=f"Account unlocked for {user.email}")


@router.delete("/users/{user_id}", response_model=AdminActionResponse)
async def delete_user(
    user_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> AdminActionResponse:
    user = (await session.scalars(select(User).where(User.id == user_id))).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    email = user.email

    # Cascade delete related records
    await session.execute(
        delete(AuthenticationAttempt).where(AuthenticationAttempt.user_id == user_id)
    )
    await session.execute(delete(AuditEvent).where(AuditEvent.user_id == user_id))
    await session.delete(user)

    session.add(AuditEvent(
        event_type="user_deleted",
        severity="critical",
        message=f"Admin deleted user {email} and purged all biometric data",
    ))

    await session.commit()

    return AdminActionResponse(success=True, message=f"User {email} and all biometric data purged")
