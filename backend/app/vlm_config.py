"""
vlm_config.py — Configuration for VLM (Vision Language Model) reasoning layer.

This module is ADDITIVE — it does not modify any existing configuration.
It provides VLM-specific settings for the hybrid authentication pipeline.

Supported models (auto-fallback order):
  1. Qwen2.5-VL-3B-Instruct (4-bit quantized, ~2.5GB VRAM, needs CUDA)
  2. moondream2 (1.9B, ~1.5GB 4-bit / ~3.8GB fp16, works on CPU)
"""

import os
import logging
from pathlib import Path

from app.config import BASE_DIR, MODEL_DIR

logger = logging.getLogger(__name__)

# ─── Paths ───────────────────────────────────────────────────────────────────
VLM_CACHE_DIR = MODEL_DIR / "vlm_cache"
VLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

VLM_REF_FRAMES_DIR = BASE_DIR / "data" / "vlm_ref_frames"
VLM_REF_FRAMES_DIR.mkdir(parents=True, exist_ok=True)

# ─── Model IDs ───────────────────────────────────────────────────────────────
QWEN_MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
MOONDREAM_MODEL_ID = "vikhyatk/moondream2"

# ─── Model Selection ────────────────────────────────────────────────────────
# Override via environment variable: VLM_MODEL=qwen | moondream | disabled
VLM_MODEL_OVERRIDE = os.getenv("VLM_MODEL", "auto")  # auto | qwen | moondream | disabled

# ─── Hardware Thresholds ────────────────────────────────────────────────────
# Minimum VRAM (GB) needed for Qwen2.5-VL-3B at 4-bit
QWEN_MIN_VRAM_GB = 3.0
# Minimum system RAM (GB) needed for moondream2 at 4-bit/fp16
MOONDREAM_MIN_RAM_GB = 4.0
# Maximum RAM the VLM should use (to stay within 8GB total)
VLM_MAX_RAM_GB = float(os.getenv("VLM_MAX_RAM_GB", "5.0"))

# ─── VLM Inference Settings ────────────────────────────────────────────────
VLM_MAX_NEW_TOKENS = 512
VLM_TEMPERATURE = 0.1  # low temperature for deterministic reasoning
VLM_TOP_P = 0.9

# ─── Reference Frame Settings ──────────────────────────────────────────────
VLM_REF_FRAME_COUNT = 3      # number of reference frames to store per user
VLM_REF_FRAME_QUALITY = 0.90  # JPEG quality for stored reference frames
VLM_AUTH_FRAME_COUNT = 3      # number of auth frames to send to VLM

# ─── VLM Decision Thresholds ───────────────────────────────────────────────
VLM_OVERALL_THRESHOLD = 0.55       # VLM overall score must be above this
VLM_VETO_CONFIDENCE = 0.85        # VLM can veto a GRANT if deny confidence > this
VLM_IDENTITY_THRESHOLD = 0.60     # VLM same_person confidence threshold
VLM_LIVENESS_THRESHOLD = 0.55     # VLM liveness confidence threshold

# ─── Fusion Weights ────────────────────────────────────────────────────────
# final_score = FUSION_TRADITIONAL_WEIGHT × trad_score
#             + FUSION_VLM_WEIGHT × vlm_score
FUSION_TRADITIONAL_WEIGHT = 0.60
FUSION_VLM_WEIGHT = 0.40

# ─── Prompt Templates ──────────────────────────────────────────────────────

VLM_JUDGE_PROMPT = """You are a facial authentication security system. Your job is to compare a registered user's face with an authentication attempt and determine if they are the same real, live person.

TASK: Analyze the provided images carefully.
- The FIRST image(s) are from the user's REGISTRATION (reference identity).
- The LAST image(s) are from the current AUTHENTICATION attempt.

Evaluate these aspects:

1. IDENTITY MATCH: Are the registration and authentication images showing the same person?
   - Compare: facial bone structure, nose shape, eye spacing, eyebrow shape, jawline, ear shape, unique marks (moles, scars).
   - Account for: different lighting, slight angle changes, natural expression variation.

2. LIVENESS: Does the authentication image show a live person in front of a real camera?
   - Look for: natural skin texture (pores, fine lines), realistic eye reflections, natural color gradients.
   - Suspicious signs: flat/uniform lighting, lack of depth, moire patterns, screen edges, paper texture.

3. AUTHENTICITY: Any signs of spoofing, deepfake, or manipulation?
   - Check for: unnatural skin smoothness, blending artifacts around face edges, inconsistent lighting angles, warping.
   - Check for: printed photo signs, screen replay signs, mask edges.

You MUST respond ONLY with a valid JSON object (no extra text before or after):
{
  "same_person": true or false,
  "same_person_confidence": 0.0 to 1.0,
  "is_live": true or false,
  "liveness_confidence": 0.0 to 1.0,
  "is_authentic": true or false,
  "authenticity_confidence": 0.0 to 1.0,
  "overall_score": 0.0 to 1.0,
  "reasoning": "Your detailed analysis explaining the decision",
  "red_flags": ["list any concerns, or empty list if none"]
}"""

VLM_JUDGE_PROMPT_SIMPLE = """Look at these face images. The first image is the registered user. The second image is an authentication attempt.

Are they the same person? Is the person in the second image real (not a photo, screen, or deepfake)?

Respond ONLY in JSON:
{
  "same_person": true/false,
  "same_person_confidence": 0.0-1.0,
  "is_live": true/false,
  "liveness_confidence": 0.0-1.0,
  "is_authentic": true/false,
  "authenticity_confidence": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "reasoning": "brief explanation",
  "red_flags": []
}"""


def detect_available_hardware():
    """Detect GPU/CPU capabilities for model selection."""
    import psutil

    info = {
        "cuda_available": False,
        "gpu_name": None,
        "vram_gb": 0.0,
        "ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 1),
        "ram_available_gb": round(psutil.virtual_memory().available / (1024 ** 3), 1),
    }

    try:
        import torch
        if torch.cuda.is_available():
            info["cuda_available"] = True
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["vram_gb"] = round(
                torch.cuda.get_device_properties(0).total_mem / (1024 ** 3), 1
            )
    except Exception:
        pass

    return info


def select_vlm_model():
    """
    Auto-select the best VLM model based on available hardware.

    Returns:
        tuple: (model_id: str, quantize: str, device: str) or (None, None, None) if disabled
    """
    if VLM_MODEL_OVERRIDE == "disabled":
        logger.info("VLM disabled via VLM_MODEL env var")
        return None, None, None

    hw = detect_available_hardware()
    logger.info(
        f"VLM hardware detection: CUDA={hw['cuda_available']}, "
        f"GPU={hw['gpu_name']}, VRAM={hw['vram_gb']}GB, "
        f"RAM={hw['ram_gb']}GB (available={hw['ram_available_gb']}GB)"
    )

    # Force a specific model if overridden
    if VLM_MODEL_OVERRIDE == "qwen":
        if hw["cuda_available"] and hw["vram_gb"] >= QWEN_MIN_VRAM_GB:
            logger.info("VLM: Using Qwen2.5-VL-3B-Instruct (forced, 4-bit, CUDA)")
            return QWEN_MODEL_ID, "4bit", "cuda"
        else:
            logger.warning("VLM: Qwen forced but insufficient GPU — trying on CPU with 4-bit")
            return QWEN_MODEL_ID, "4bit", "cpu"

    if VLM_MODEL_OVERRIDE == "moondream":
        device = "cuda" if hw["cuda_available"] else "cpu"
        logger.info(f"VLM: Using moondream2 (forced, {device})")
        return MOONDREAM_MODEL_ID, "fp16", device

    # Auto selection
    # Priority 1: Qwen on GPU (best accuracy)
    if hw["cuda_available"] and hw["vram_gb"] >= QWEN_MIN_VRAM_GB:
        logger.info("VLM auto-selected: Qwen2.5-VL-3B-Instruct (4-bit, CUDA)")
        return QWEN_MODEL_ID, "4bit", "cuda"

    # Priority 2: moondream2 (works on CPU, fits in 8GB RAM)
    if hw["ram_available_gb"] >= MOONDREAM_MIN_RAM_GB:
        device = "cuda" if hw["cuda_available"] else "cpu"
        logger.info(f"VLM auto-selected: moondream2 ({device})")
        return MOONDREAM_MODEL_ID, "fp16", device

    # Not enough resources
    logger.warning(
        f"VLM: Insufficient resources (VRAM={hw['vram_gb']}GB, "
        f"RAM_avail={hw['ram_available_gb']}GB). VLM disabled."
    )
    return None, None, None
