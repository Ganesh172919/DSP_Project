"""SQLAlchemy ORM models for DeepShield Guardian.

Tables:
- User: identity, encrypted biometric template, security metadata
- EnrollmentSession: multi-step registration flow state
- AuthenticationAttempt: challenge-response auth lifecycle
- AuditEvent: security audit trail
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, JSON, LargeBinary,
    String, Text, Index,
)
from sqlalchemy.orm import DeclarativeBase


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(String(32), primary_key=True, default=_new_id)
    email = Column(String(320), unique=True, nullable=False, index=True)
    full_name = Column(String(160), nullable=False)
    password_hash = Column(String(128), nullable=False)

    # Biometric template (AES-256-GCM encrypted blob)
    biometric_template = Column(LargeBinary, nullable=True)
    biometric_salt = Column(LargeBinary, nullable=True)
    template_quality_score = Column(Float, default=0.0)
    security_score = Column(Float, default=0.0)

    # Registration state
    registration_completed = Column(Boolean, default=False)
    registered_at = Column(DateTime, nullable=True)

    # Re-enrollment tracking
    re_enrollment_due_at = Column(DateTime, nullable=True)

    # Security: account lockout
    failed_consecutive_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_authenticated_at = Column(DateTime, nullable=True)

    # Device tracking
    device_fingerprints = Column(JSON, default=list)

    # Accessibility preferences
    accessibility_profile = Column(JSON, default=dict)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_locked", "locked_until"),
    )


class EnrollmentSession(Base):
    __tablename__ = "enrollment_sessions"

    id = Column(String(32), primary_key=True, default=_new_id)
    user_id = Column(String(32), nullable=False, index=True)
    status = Column(String(20), default="active")  # active, completed, expired
    captures = Column(JSON, default=list)
    quality_scores = Column(JSON, default=list)

    # Multi-angle tracking
    completed_steps = Column(JSON, default=list)
    total_frames_captured = Column(Integer, default=0)

    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    completed_at = Column(DateTime, nullable=True)


class AuthenticationAttempt(Base):
    __tablename__ = "authentication_attempts"

    id = Column(String(32), primary_key=True, default=_new_id)
    user_id = Column(String(32), nullable=False, index=True)
    status = Column(String(20), default="active")  # active, approved, denied, expired
    challenges = Column(JSON, default=list)
    observations = Column(JSON, default=list)
    stage_results = Column(JSON, default=list)
    final_score = Column(Float, nullable=True)

    # Security context
    security_level = Column(String(20), default="enhanced")
    attempt_number = Column(Integer, default=1)  # Which attempt this is (for lockout)
    denial_reasons = Column(JSON, default=list)
    anomalies = Column(JSON, default=list)

    # Per-stage latency (ms)
    stage_latencies = Column(JSON, default=dict)

    # Review flag
    needs_review = Column(Boolean, default=False)

    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_attempts_user_status", "user_id", "status"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(32), primary_key=True, default=_new_id)
    event_type = Column(String(60), nullable=False, index=True)
    severity = Column(String(20), default="info")  # info, warning, critical
    user_id = Column(String(32), nullable=True, index=True)
    attempt_id = Column(String(32), nullable=True)
    message = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_utcnow)

    __table_args__ = (
        Index("idx_audit_type_severity", "event_type", "severity"),
    )
