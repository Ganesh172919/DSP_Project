"""
db/vlm_models.py — SQLAlchemy ORM model for VLM reference frames.

This is ADDITIVE — does not modify existing db/models.py.

Frames are stored on DISK in data/vlm_ref_frames/{user_id}/.
The DB only stores metadata (path, count, quality).
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.models import Base, engine


class VLMRegistration(Base):
    __tablename__ = "vlm_registrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    frames_dir = Column(String, nullable=False)    # disk path to folder with JPEG frames
    frame_count = Column(Integer, default=0)       # number of frames stored
    avg_quality = Column(Float, default=0.0)       # average face quality
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User")

    def __repr__(self):
        return (
            f"<VLMRegistration(id={self.id}, user_id={self.user_id}, "
            f"frames={self.frame_count}, dir='{self.frames_dir}')>"
        )


def init_vlm_tables():
    """Create VLM tables if they don't exist. Safe to call multiple times."""
    Base.metadata.create_all(bind=engine, tables=[VLMRegistration.__table__])
