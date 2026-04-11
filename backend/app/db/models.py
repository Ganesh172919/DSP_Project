"""
db/models.py — SQLAlchemy ORM models for the Facial Recognition Auth System.

Tables:
  users      — registered identities with encrypted face embeddings
  auth_logs  — audit trail of every authentication attempt
"""

import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, LargeBinary, DateTime, Text,
    create_engine, ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from app.config import DATABASE_URL

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(256), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=True)  # optional — face is primary auth
    embedding_enc = Column(LargeBinary, nullable=False)  # AES-256-GCM encrypted 512-d vector
    face_quality = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    auth_logs = relationship("AuthLog", back_populates="user", lazy="dynamic")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class AuthLog(Base):
    __tablename__ = "auth_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    liveness_score = Column(Float, nullable=True)
    deepfake_score = Column(Float, nullable=True)
    similarity_score = Column(Float, nullable=True)
    injection_confidence = Column(Float, nullable=True)
    threat_flags = Column(Text, default="[]")  # JSON array of flag strings
    decision = Column(String(16), nullable=False)  # "GRANT" or "DENY"
    denial_reason = Column(String(64), nullable=True)

    user = relationship("User", back_populates="auth_logs")

    def get_threat_flags(self) -> list:
        return json.loads(self.threat_flags) if self.threat_flags else []

    def set_threat_flags(self, flags: list):
        self.threat_flags = json.dumps(flags)

    def __repr__(self):
        return f"<AuthLog(id={self.id}, decision='{self.decision}')>"


class ChallengeLog(Base):
    __tablename__ = "challenge_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    challenge_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    instruction_ids = Column(Text, nullable=False)       # JSON array of instruction IDs
    instruction_results = Column(Text, default="[]")     # JSON array of pass/fail + scores
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    expired = Column(Integer, default=0)                  # 1 if TTL exceeded

    user = relationship("User")

    def get_instruction_ids(self) -> list:
        return json.loads(self.instruction_ids) if self.instruction_ids else []

    def get_instruction_results(self) -> list:
        return json.loads(self.instruction_results) if self.instruction_results else []

    def __repr__(self):
        return f"<ChallengeLog(id={self.id}, challenge_id='{self.challenge_id}')>"


# ─── Engine & Session Factory ───────────────────────────────────────────────

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session, auto-closes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
