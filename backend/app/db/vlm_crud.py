"""
db/vlm_crud.py — Data-access helpers for VLM reference frames.

This is ADDITIVE — does not modify existing db/crud.py.

Reference frames are stored as JPEG files on DISK in:
  data/vlm_ref_frames/{user_id}/frame_0.jpg, frame_1.jpg, ...

The DB only stores metadata (folder path, count, quality).
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.db.vlm_models import VLMRegistration

logger = logging.getLogger(__name__)

# ─── Base directory for frame storage ────────────────────────────────────────
_BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
VLM_FRAMES_DIR = _BASE_DIR / "data" / "vlm_ref_frames"
VLM_FRAMES_DIR.mkdir(parents=True, exist_ok=True)


def _user_frames_dir(user_id: int) -> Path:
    """Get the disk folder for a user's reference frames."""
    d = VLM_FRAMES_DIR / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


# ─── CRUD Operations ───────────────────────────────────────────────────────

def store_vlm_reference_frames(
    db: Session,
    user_id: int,
    frames: list[np.ndarray],
    qualities: list[float],
) -> int:
    """
    Save reference frames to DISK and record metadata in DB.

    Args:
        db: SQLAlchemy session
        user_id: registered user ID
        frames: list of BGR numpy arrays
        qualities: face quality scores for each frame

    Returns: number of frames stored
    """
    # Delete any existing frames for this user (re-registration)
    delete_vlm_reference_frames(db, user_id)

    folder = _user_frames_dir(user_id)
    saved = 0

    for i, frame in enumerate(frames):
        try:
            path = folder / f"frame_{i}.jpg"
            cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            if path.exists():
                saved += 1
            else:
                logger.error(f"Failed to write frame {i} to {path}")
        except Exception as e:
            logger.error(f"Failed to save frame {i} for user {user_id}: {e}")

    # Store metadata in DB
    avg_q = sum(qualities) / len(qualities) if qualities else 0.0
    record = VLMRegistration(
        user_id=user_id,
        frames_dir=str(folder),
        frame_count=saved,
        avg_quality=avg_q,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    logger.info(f"Stored {saved} VLM reference frames on disk for user {user_id} → {folder}")
    return saved


def get_vlm_reference_frames(db: Session, user_id: int) -> list[np.ndarray]:
    """
    Load reference frames from DISK for a user.

    Returns: list of BGR numpy arrays, ordered by frame index
    """
    record = (
        db.query(VLMRegistration)
        .filter(VLMRegistration.user_id == user_id)
        .first()
    )

    if record is None:
        return []

    folder = Path(record.frames_dir)
    if not folder.exists():
        logger.warning(f"VLM frames folder missing for user {user_id}: {folder}")
        return []

    frames = []
    for i in range(record.frame_count):
        path = folder / f"frame_{i}.jpg"
        if path.exists():
            frame = cv2.imread(str(path))
            if frame is not None:
                frames.append(frame)
            else:
                logger.warning(f"Failed to read frame {path}")
        else:
            logger.warning(f"Frame file missing: {path}")

    logger.info(f"Loaded {len(frames)} VLM reference frames from disk for user {user_id}")
    return frames


def has_vlm_reference_frames(db: Session, user_id: int) -> bool:
    """Check if a user has VLM reference frames stored."""
    record = (
        db.query(VLMRegistration)
        .filter(VLMRegistration.user_id == user_id)
        .first()
    )
    return record is not None and record.frame_count > 0


def delete_vlm_reference_frames(db: Session, user_id: int) -> int:
    """
    Delete all VLM reference frames (disk + DB) for a user.

    Returns: number of deleted records
    """
    record = (
        db.query(VLMRegistration)
        .filter(VLMRegistration.user_id == user_id)
        .first()
    )

    if record is None:
        return 0

    # Delete folder from disk
    folder = Path(record.frames_dir)
    if folder.exists():
        try:
            shutil.rmtree(folder)
            logger.info(f"Deleted VLM frames folder: {folder}")
        except Exception as e:
            logger.error(f"Failed to delete folder {folder}: {e}")

    # Delete DB record
    db.delete(record)
    db.commit()

    logger.info(f"Deleted VLM registration for user {user_id}")
    return 1
