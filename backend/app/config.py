"""
config.py — Central configuration for the Facial Recognition Auth System.
All thresholds, model paths, and environment-driven secrets live here.
"""

import os
import torch
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
MODEL_DIR = BASE_DIR / "weights"
DB_PATH = BASE_DIR / "data" / "auth.db"
FAISS_INDEX_PATH = BASE_DIR / "data" / "face.index"

# Ensure directories exist
MODEL_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

# ─── Device ──────────────────────────────────────────────────────────────────
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ─── Layer 0: Anti-Injection ─────────────────────────────────────────────────
VIRTUAL_CAMERA_SIGNATURES = [
    "OBS Virtual Camera", "OBS-Camera", "ManyCam",
    "v4l2loopback", "DroidCam", "EpocCam", "XSplit VCam",
    "Snap Camera", "CamTwist", "ChromaCam",
]
PRNU_VARIANCE_THRESHOLD = 0.5        # real sensors show variance > this
INJECTION_CONFIDENCE_THRESHOLD = 0.7

# ─── Layer 1: Face Detection ────────────────────────────────────────────────
FACE_CONFIDENCE_THRESHOLD = 0.70       # YuNet scores run 0.7-0.95 for valid faces
MIN_FACE_AREA_RATIO = 0.05           # face must be ≥5% of frame area
MAX_YAW_DEGREES = 30.0
MAX_PITCH_DEGREES = 20.0
ALIGNED_FACE_SIZE = (112, 112)

# ─── Layer 2: ArcFace Recognition ───────────────────────────────────────────
EMBEDDING_DIM = 512
SIMILARITY_THRESHOLD = 0.40          # cosine similarity threshold
REGISTRATION_FRAMES = 5             # number of frames to average for template

# ─── Layer 3: Liveness ──────────────────────────────────────────────────────
LIVENESS_CNN_THRESHOLD = 0.85
RPPG_WINDOW_SECONDS = 3.0
RPPG_FPS = 30
RPPG_MIN_BPM = 45.0
RPPG_MAX_BPM = 180.0
RPPG_BANDPASS_LOW = 0.75             # Hz
RPPG_BANDPASS_HIGH = 3.0             # Hz
RPPG_SIGNAL_QUALITY_THRESHOLD = 0.4

# Active challenge thresholds
EAR_BLINK_THRESHOLD = 0.2
BLINK_CONSECUTIVE_FRAMES = 2
HEAD_TURN_YAW_DELTA = 20.0           # degrees
HEAD_TURN_TIME_WINDOW = 2.0          # seconds
SMILE_LIP_DISTANCE_THRESHOLD = 0.05  # normalized

# Fusion
FUSION_FINAL_THRESHOLD = 0.70

# ─── Layer 4: Deepfake Detection ────────────────────────────────────────────
SPECTRAL_BANDS = 32
DEEPFAKE_SPECTRAL_WEIGHT = 0.4
DEEPFAKE_CNN_WEIGHT = 0.6
DEEPFAKE_FLAG_THRESHOLD = 0.30
BOUNDARY_ARTIFACT_THRESHOLD = 0.25
EYE_REFLECTION_THRESHOLD = 0.3
SKIN_UNIFORMITY_THRESHOLD = 0.4
COLOR_CORRELATION_THRESHOLD = 0.3
TEMPORAL_FLICKER_THRESHOLD = 0.2

# ─── Layer 5: Instruction Challenges ───────────────────────────────────────
CHALLENGE_COUNT = 2                    # instructions per auth attempt
CHALLENGE_TTL_SECONDS = 300            # 5-minute window to complete
INSTRUCTION_VIDEO_FPS = 30
INSTRUCTION_VIDEO_DURATION_SEC = 4     # seconds per instruction video
INSTRUCTION_MIN_CONFIDENCE = 0.60      # min confidence to pass instruction
INSTRUCTION_CATEGORIES = ["face", "hand"]

# ─── Enhanced Liveness Thresholds ─────────────────────────────────────────
MOIRE_FFT_THRESHOLD = 0.15
OPTICAL_FLOW_MIN_MOVEMENT = 0.5
MICRO_MOVEMENT_THRESHOLD = 0.3
LBP_TEXTURE_THRESHOLD = 0.6
COLOR_DISTRIBUTION_THRESHOLD = 0.5
FACE_BOUNDARY_THRESHOLD = 0.3

# ─── Security ───────────────────────────────────────────────────────────────
AES_KEY = os.getenv("FACE_AUTH_AES_KEY", "0" * 64)   # 256-bit hex key; MUST override in prod
JWT_PRIVATE_KEY_PATH = os.getenv("JWT_PRIVATE_KEY", str(BASE_DIR / "keys" / "private.pem"))
JWT_PUBLIC_KEY_PATH = os.getenv("JWT_PUBLIC_KEY", str(BASE_DIR / "keys" / "public.pem"))
JWT_ALGORITHM = "RS256"
JWT_EXPIRY_MINUTES = 15
RATE_LIMIT = "5/minute"

# ─── Database ───────────────────────────────────────────────────────────────
DATABASE_URL = f"sqlite:///{DB_PATH}"
