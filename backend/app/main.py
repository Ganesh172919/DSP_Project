"""
main.py — FastAPI Application

Single entry point wiring the AI pipeline to HTTP.

Endpoints:
  POST /api/v1/register     — Register a new face identity
  POST /api/v1/authenticate  — Authenticate against stored identity
  GET  /api/v1/users/{user_id}/history — Auth attempt history

Security: JWT RS256, SlowAPI rate limiting, AES-256 encrypted embeddings.
"""

import io
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List

import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import RATE_LIMIT, CHALLENGE_TTL_SECONDS
from app.db.models import init_db, get_db
from app.db import crud
from app.crypto import encrypt_embedding, decrypt_embedding, create_jwt
from app.pipeline import AuthPipeline
from app.instructions import pick_random_instructions, get_all_instructions, get_instruction_stats

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ─── App Init ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Facial Recognition Auth System",
    description="Production-grade facial authentication with anti-spoofing, "
                "deepfake detection, and liveness verification.",
    version="1.0.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Max 5 attempts per minute."},
    )


# ─── Startup ────────────────────────────────────────────────────────────────
pipeline: Optional[AuthPipeline] = None


@app.on_event("startup")
def startup():
    global pipeline
    init_db()
    pipeline = AuthPipeline()
    logger.info("Application started — DB initialized, pipeline loaded")


# ─── Helpers ────────────────────────────────────────────────────────────────

def decode_image(file_bytes: bytes) -> np.ndarray:
    """Decode uploaded JPEG/PNG bytes to BGR numpy array."""
    arr = np.frombuffer(file_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image data")
    return img


async def read_frames_from_upload(file: UploadFile, num_frames: int = 5) -> list[np.ndarray]:
    """
    Extract frames from uploaded file.
    Supports:
      - Single JPEG → [frame]
      - Video file → extract num_frames evenly spaced
      - Multiple JPEG bytes concatenation (multipart)
    """
    content = await file.read()

    # Try as single image first
    img = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is not None:
        return [img]

    # Try as video
    import tempfile
    import os

    tmp_path = os.path.join("data", f"tmp_{uuid.uuid4().hex}.mp4")
    try:
        with open(tmp_path, "wb") as f:
            f.write(content)

        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Cannot decode file as image or video")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames < num_frames:
            num_frames = max(total_frames, 1)

        indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        frames = []

        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if ret:
                frames.append(frame)

        cap.release()
        return frames

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/register")
@limiter.limit(RATE_LIMIT)
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    face_data: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Register a new face identity.

    Accepts multiple face image files (5 recommended).
    Runs liveness + detection on each, averages embeddings.

    Returns: {user_id, liveness_score, face_quality, status}
    """
    # Check if user already exists
    existing = crud.get_user_by_username(db, username)
    if existing:
        raise HTTPException(status_code=409, detail=f"Username '{username}' already registered")

    existing_email = crud.get_user_by_email(db, email)
    if existing_email:
        raise HTTPException(status_code=409, detail=f"Email '{email}' already registered")

    # Decode all uploaded images into frames
    frames = []
    for upload in face_data:
        content = await upload.read()
        img = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is not None:
            frames.append(img)

    if len(frames) < 1:
        raise HTTPException(status_code=400, detail="No valid images uploaded")

    logger.info(f"Registration: received {len(frames)} frames for user '{username}'")

    try:
        # Run registration pipeline
        template, liveness_score, face_quality = pipeline.register_face(
            frames, skip_injection_check=True
        )

        # Encrypt embedding
        encrypted = encrypt_embedding(template)

        # Store in DB
        user = crud.create_user(
            db=db,
            username=username,
            email=email,
            embedding_enc=encrypted,
            face_quality=face_quality,
        )

        logger.info(f"Registered user '{username}' (id={user.id})")

        return {
            "user_id": user.id,
            "username": username,
            "liveness_score": round(liveness_score, 4),
            "face_quality": round(face_quality, 4),
            "status": "registered",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Registration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Registration failed — see server logs")


@app.post("/api/v1/authenticate")
@limiter.limit(RATE_LIMIT)
async def authenticate(
    request: Request,
    username: str = Form(...),
    face_data: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Authenticate a user against their stored face template.

    Steps: run full 4-layer pipeline → decision engine.

    Returns: {authenticated, confidence, threat_flags, jwt_token}
    """
    # Look up user
    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    # Decrypt stored embedding
    stored_embedding = decrypt_embedding(user.embedding_enc)

    # Get frame(s)
    frames = await read_frames_from_upload(face_data, num_frames=1)
    if not frames:
        raise HTTPException(status_code=400, detail="No valid frame extracted")

    frame = frames[0]

    # Run full pipeline
    result = pipeline.authenticate(
        frame=frame,
        stored_embedding=stored_embedding,
        skip_injection_check=True,  # skip for uploaded files
        frames_for_liveness=frames if len(frames) > 1 else None,
    )

    # Get client IP
    client_ip = request.client.host if request.client else "unknown"

    # Log to audit table
    crud.log_auth_attempt(
        db=db,
        user_id=user.id,
        ip_address=client_ip,
        liveness_score=result.scores.liveness_score,
        deepfake_score=result.scores.deepfake_score,
        similarity_score=result.scores.similarity_score,
        injection_confidence=result.scores.injection_confidence,
        threat_flags=result.threat_flags,
        decision=result.decision,
        denial_reason=result.denial_reason,
    )

    # Build response
    response = {
        "authenticated": result.decision == "GRANT",
        "confidence": result.confidence,
        "threat_flags": result.threat_flags,
        "scores": {
            "liveness": result.scores.liveness_score,
            "deepfake": result.scores.deepfake_score,
            "similarity": result.scores.similarity_score,
            "injection": result.scores.injection_confidence,
        },
        "processing_time_ms": round(result.processing_time_ms, 1),
    }

    if result.decision == "GRANT":
        response["jwt_token"] = create_jwt(str(user.id), user.username)
    else:
        response["denial_reason"] = result.denial_reason

    return response


# ═══════════════════════════════════════════════════════════════════════════
# VIDEO-BASED AUTH (no instructions)
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/authenticate/video")
@limiter.limit(RATE_LIMIT)
async def authenticate_video(
    request: Request,
    username: str = Form(...),
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Authenticate via video recording (no instruction challenges).

    Accepts:
      - username: the registered user
      - video: webcam recording (WebM/MP4)

    Pipeline extracts frames from the video and runs:
      - Face detection + alignment (middle frame)
      - ArcFace identity verification
      - Multi-frame liveness detection (CNN + anti-spoof checks)
      - Deepfake detection (spectral + CNN + temporal)

    Returns: {authenticated, confidence, scores, jwt_token}
    """
    # Look up user
    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    # Decrypt stored embedding
    stored_embedding = decrypt_embedding(user.embedding_enc)

    # Read video bytes
    video_bytes = await video.read()
    if not video_bytes:
        raise HTTPException(status_code=400, detail="Empty video file")

    # Run video-based pipeline
    result = pipeline.authenticate_video(
        stored_embedding=stored_embedding,
        video_bytes=video_bytes,
    )

    # Get client IP
    client_ip = request.client.host if request.client else "unknown"

    # Log to audit table
    crud.log_auth_attempt(
        db=db,
        user_id=user.id,
        ip_address=client_ip,
        liveness_score=result.scores.liveness_score,
        deepfake_score=result.scores.deepfake_score,
        similarity_score=result.scores.similarity_score,
        injection_confidence=result.scores.injection_confidence,
        threat_flags=result.threat_flags,
        decision=result.decision,
        denial_reason=result.denial_reason,
    )

    # Build response
    response = {
        "authenticated": result.decision == "GRANT",
        "confidence": result.confidence,
        "threat_flags": result.threat_flags,
        "scores": {
            "liveness": result.scores.liveness_score,
            "deepfake": result.scores.deepfake_score,
            "similarity": result.scores.similarity_score,
            "injection": result.scores.injection_confidence,
        },
        "processing_time_ms": round(result.processing_time_ms, 1),
    }

    if result.decision == "GRANT":
        response["jwt_token"] = create_jwt(str(user.id), user.username)
    else:
        response["denial_reason"] = result.denial_reason

    return response


# ═══════════════════════════════════════════════════════════════════════════
# CHALLENGE ENDPOINTS (LEGACY)
# ═══════════════════════════════════════════════════════════════════════════

# In-memory store for active challenges (TTL-based)
_active_challenges: dict[str, dict] = {}


@app.get("/api/v1/challenge")
async def get_challenge(db: Session = Depends(get_db)):
    """
    Issue an authentication challenge.

    Picks 2 random instructions (1 face + 1 hand) and returns them.
    The challenge_id must be submitted with the authentication request.
    Challenge expires after 5 minutes.

    Returns: {challenge_id, instructions: [{id, text, category, duration_sec}]}
    """
    instructions = pick_random_instructions(count=2, categories=["face", "hand"])
    challenge_id = uuid.uuid4().hex

    inst_data = [
        {
            "id": inst["id"],
            "text": inst["text"],
            "category": inst["category"],
            "duration_sec": inst["duration_sec"],
        }
        for inst in instructions
    ]

    # Store challenge in memory + DB
    _active_challenges[challenge_id] = {
        "instructions": instructions,
        "created_at": datetime.now(timezone.utc),
    }

    # Store in DB
    crud.create_challenge(
        db=db,
        challenge_id=challenge_id,
        instruction_ids=[inst["id"] for inst in instructions],
    )

    logger.info(f"Challenge issued: {challenge_id} → instructions={[i['id'] for i in instructions]}")

    return {
        "challenge_id": challenge_id,
        "instructions": inst_data,
        "ttl_seconds": CHALLENGE_TTL_SECONDS,
    }


@app.post("/api/v1/authenticate/challenge")
@limiter.limit(RATE_LIMIT)
async def authenticate_with_challenge(
    request: Request,
    username: str = Form(...),
    challenge_id: str = Form(...),
    video_1: UploadFile = File(...),
    video_2: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Authenticate with instruction challenges.

    Accepts:
      - username: the registered user
      - challenge_id: from GET /api/v1/challenge
      - video_1: video of user performing instruction 1
      - video_2: video of user performing instruction 2

    Returns: {authenticated, confidence, scores, instruction_results, jwt_token}
    """
    # Validate challenge
    challenge = _active_challenges.get(challenge_id)
    if not challenge:
        # Check DB fallback
        db_challenge = crud.get_challenge(db, challenge_id)
        if db_challenge is None:
            raise HTTPException(status_code=400, detail="Invalid or expired challenge_id")
        # Reconstruct from DB
        from app.instructions import get_instruction
        inst_ids = db_challenge.get_instruction_ids()
        instructions = [get_instruction(i) for i in inst_ids]
        if any(inst is None for inst in instructions):
            raise HTTPException(status_code=400, detail="Invalid instructions in challenge")
        challenge = {
            "instructions": instructions,
            "created_at": db_challenge.created_at,
        }

    # Check TTL
    elapsed = (datetime.now(timezone.utc) - challenge["created_at"]).total_seconds()
    if elapsed > CHALLENGE_TTL_SECONDS:
        _active_challenges.pop(challenge_id, None)
        raise HTTPException(status_code=400, detail="Challenge expired")

    # Look up user
    user = crud.get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    # Decrypt stored embedding
    stored_embedding = decrypt_embedding(user.embedding_enc)

    # Read video bytes
    video_1_bytes = await video_1.read()
    video_2_bytes = await video_2.read()

    if not video_1_bytes or not video_2_bytes:
        raise HTTPException(status_code=400, detail="Both video files are required")

    # Get instruction IDs
    instructions = challenge["instructions"]
    instruction_ids = [inst["id"] for inst in instructions]

    # Run full pipeline with challenges
    result = pipeline.authenticate_with_challenges(
        stored_embedding=stored_embedding,
        instruction_ids=instruction_ids,
        video_data_list=[video_1_bytes, video_2_bytes],
        skip_injection_check=True,
    )

    # Clean up challenge
    _active_challenges.pop(challenge_id, None)

    # Get client IP
    client_ip = request.client.host if request.client else "unknown"

    # Log to audit table
    crud.log_auth_attempt(
        db=db,
        user_id=user.id,
        ip_address=client_ip,
        liveness_score=result.scores.liveness_score,
        deepfake_score=result.scores.deepfake_score,
        similarity_score=result.scores.similarity_score,
        injection_confidence=result.scores.injection_confidence,
        threat_flags=result.threat_flags,
        decision=result.decision,
        denial_reason=result.denial_reason,
    )

    # Log challenge result
    crud.complete_challenge(
        db=db,
        challenge_id=challenge_id,
        user_id=user.id,
        instruction_results=[
            {"id": ir.instruction_id, "passed": ir.passed,
             "confidence": ir.confidence, "detail": ir.detail}
            for ir in result.instruction_results
        ],
    )

    # Build response
    response = {
        "authenticated": result.decision == "GRANT",
        "confidence": result.confidence,
        "threat_flags": result.threat_flags,
        "scores": {
            "liveness": result.scores.liveness_score,
            "deepfake": result.scores.deepfake_score,
            "similarity": result.scores.similarity_score,
            "injection": result.scores.injection_confidence,
            "instruction_scores": result.scores.instruction_scores,
        },
        "instruction_results": [
            {
                "instruction_id": ir.instruction_id,
                "passed": ir.passed,
                "confidence": round(ir.confidence, 4),
                "detail": ir.detail,
                "frames_analyzed": ir.frames_analyzed,
            }
            for ir in result.instruction_results
        ],
        "processing_time_ms": round(result.processing_time_ms, 1),
    }

    if result.decision == "GRANT":
        response["jwt_token"] = create_jwt(str(user.id), user.username)
    else:
        response["denial_reason"] = result.denial_reason

    return response


@app.get("/api/v1/instructions")
async def list_instructions():
    """List all available instructions and stats (for debugging/testing)."""
    return {
        "instructions": get_all_instructions(),
        "stats": get_instruction_stats(),
    }


@app.get("/api/v1/users/{user_id}/history")
async def auth_history(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Get the last 10 authentication attempts for a user.

    Returns: list of auth attempts with scores and flags.
    """
    user = crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    logs = crud.get_auth_history(db, user_id, limit=10)

    return {
        "user_id": user_id,
        "username": user.username,
        "history": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "ip_address": log.ip_address,
                "decision": log.decision,
                "denial_reason": log.denial_reason,
                "scores": {
                    "liveness": log.liveness_score,
                    "deepfake": log.deepfake_score,
                    "similarity": log.similarity_score,
                    "injection": log.injection_confidence,
                },
                "threat_flags": log.get_threat_flags(),
            }
            for log in logs
        ],
    }


# ─── Health check ───────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "pipeline_loaded": pipeline is not None}
