"""
db/crud.py — Data-access helpers for users and auth logs.
"""

import json
from typing import Optional
from sqlalchemy.orm import Session

from app.db.models import User, AuthLog


# ═══════════════════════════════════════════════════════════════════════════
# User operations
# ═══════════════════════════════════════════════════════════════════════════

def create_user(
    db: Session,
    username: str,
    email: str,
    embedding_enc: bytes,
    face_quality: float = 0.0,
    password_hash: Optional[str] = None,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        embedding_enc=embedding_enc,
        face_quality=face_quality,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


# ═══════════════════════════════════════════════════════════════════════════
# Auth log operations
# ═══════════════════════════════════════════════════════════════════════════

def log_auth_attempt(
    db: Session,
    user_id: Optional[int],
    ip_address: str,
    liveness_score: Optional[float],
    deepfake_score: Optional[float],
    similarity_score: Optional[float],
    injection_confidence: Optional[float],
    threat_flags: list,
    decision: str,
    denial_reason: Optional[str] = None,
) -> AuthLog:
    log = AuthLog(
        user_id=user_id,
        ip_address=ip_address,
        liveness_score=liveness_score,
        deepfake_score=deepfake_score,
        similarity_score=similarity_score,
        injection_confidence=injection_confidence,
        threat_flags=json.dumps(threat_flags),
        decision=decision,
        denial_reason=denial_reason,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_auth_history(db: Session, user_id: int, limit: int = 10) -> list[AuthLog]:
    return (
        db.query(AuthLog)
        .filter(AuthLog.user_id == user_id)
        .order_by(AuthLog.timestamp.desc())
        .limit(limit)
        .all()
    )


# ═══════════════════════════════════════════════════════════════════════════
# Challenge operations
# ═══════════════════════════════════════════════════════════════════════════

from app.db.models import ChallengeLog


def create_challenge(
    db: Session,
    challenge_id: str,
    instruction_ids: list[int],
) -> ChallengeLog:
    log = ChallengeLog(
        challenge_id=challenge_id,
        instruction_ids=json.dumps(instruction_ids),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_challenge(db: Session, challenge_id: str) -> Optional[ChallengeLog]:
    return db.query(ChallengeLog).filter(ChallengeLog.challenge_id == challenge_id).first()


def complete_challenge(
    db: Session,
    challenge_id: str,
    user_id: int,
    instruction_results: list[dict],
) -> Optional[ChallengeLog]:
    from datetime import datetime, timezone
    log = get_challenge(db, challenge_id)
    if log is None:
        return None
    log.user_id = user_id
    log.instruction_results = json.dumps(instruction_results)
    log.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(log)
    return log

