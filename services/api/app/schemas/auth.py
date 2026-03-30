"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# ── Registration ──

class RegistrationStartRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    accessibility_profile: dict[str, bool] = Field(default_factory=dict)


class RegistrationStartResponse(BaseModel):
    session_id: str
    expires_at: datetime


class ObservationFrame(BaseModel):
    step: str
    frame_b64: str | None = None
    landmarks: list[list[float]] = Field(default_factory=list)
    hand_landmarks: list[list[list[float]]] = Field(default_factory=list)
    client_metrics: dict[str, Any] = Field(default_factory=dict)
    captured_at: datetime
    challenge_id: str | None = None


class FrameAckResponse(BaseModel):
    accepted: bool
    quality_score: float
    guidance: list[str]
    step: str | None = None
    steps_remaining: int = 0


class RegistrationCompleteResponse(BaseModel):
    user_id: str
    quality_score: float
    security_score: float
    steps_completed: int = 0
    total_frames: int = 0


# ── Authentication ──

class AuthenticationStartRequest(BaseModel):
    email: EmailStr
    security_level: str = "enhanced"


class ChallengeResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    duration_seconds: int


class AuthenticationStartResponse(BaseModel):
    attempt_id: str
    challenges: list[ChallengeResponse]
    attempt_number: int = 1
    max_attempts: int = 3


class StageResult(BaseModel):
    stage: str
    label: str = ""
    score: float
    passed: bool
    message: str
    weight: float = 0.0
    threshold: float = 0.0


class AuthenticationStateResponse(BaseModel):
    attempt_id: str
    stage_results: list[StageResult]
    final_score: float | None = None
    authenticated: bool | None = None
    anomalies: list[str] = Field(default_factory=list)
    needs_review: bool = False
    attempts_remaining: int = 3


# ── Admin ──

class DashboardMetrics(BaseModel):
    total_authentications: int
    success_rate: float
    blocked_attacks: int
    average_latency_ms: float
    active_alerts: int
    recent_events: list[dict[str, Any]]
    challenge_success_rates: dict[str, float] = Field(default_factory=dict)
    attack_type_counts: dict[str, int] = Field(default_factory=dict)


class UserListItem(BaseModel):
    id: str
    email: str
    full_name: str
    registration_completed: bool
    security_score: float
    failed_attempts: int
    locked: bool
    created_at: str


class UserListResponse(BaseModel):
    users: list[UserListItem]
    total: int


class AdminActionResponse(BaseModel):
    success: bool
    message: str


# ── Profile ──

class UserProfileResponse(BaseModel):
    full_name: str
    email: EmailStr
    registration_completed: bool
    template_quality_score: float
    security_score: float
    re_enrollment_due: str | None = None
    recent_attempts: list[dict[str, Any]]
