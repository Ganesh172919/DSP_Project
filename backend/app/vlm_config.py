"""
vlm_config.py — Configuration for VLM (Vision Language Model) reasoning layer.

This module is ADDITIVE — it does not modify any existing configuration.
It provides VLM-specific settings for the hybrid authentication pipeline.

Supported models (auto-fallback order):
  1. Qwen2.5-VL-3B-Instruct (4-bit quantized, ~2.5GB VRAM, needs CUDA)
  2. moondream2 (1.9B, best CPU quality when memory allows)
  3. SmolVLM-256M-Instruct (lightweight CPU fallback for 8GB systems)
"""

import os
import logging
from pathlib import Path

from app.config import BASE_DIR, MODEL_DIR

logger = logging.getLogger(__name__)

# Hugging Face's Xet-backed download path can fail on some Windows setups.
# Falling back to standard HTTP downloads is slower but more reliable here.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

# ─── Paths ───────────────────────────────────────────────────────────────────
VLM_CACHE_DIR = MODEL_DIR / "vlm_cache"
VLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)

VLM_REF_FRAMES_DIR = BASE_DIR / "data" / "vlm_ref_frames"
VLM_REF_FRAMES_DIR.mkdir(parents=True, exist_ok=True)

# ─── Model IDs ───────────────────────────────────────────────────────────────
QWEN_MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"
MOONDREAM_MODEL_ID = "vikhyatk/moondream2"
MOONDREAM_MODEL_REVISION = os.getenv("MOONDREAM_REVISION", "2025-06-21")
SMOLVLM_MODEL_ID = "HuggingFaceTB/SmolVLM-256M-Instruct"

# ─── Model Selection ────────────────────────────────────────────────────────
# Override via environment variable: VLM_MODEL=qwen | moondream | smolvlm | disabled
VLM_MODEL_OVERRIDE = os.getenv("VLM_MODEL", "auto")  # auto | qwen | moondream | smolvlm | disabled

# ─── Hardware Thresholds ────────────────────────────────────────────────────
# Minimum VRAM (GB) needed for Qwen2.5-VL-3B at 4-bit
QWEN_MIN_VRAM_GB = 3.0
# Minimum total system RAM (GB) needed for moondream2 on CPU
MOONDREAM_MIN_RAM_GB = 6.0
# Preferred free RAM before loading moondream2 without warnings
MOONDREAM_RECOMMENDED_AVAILABLE_RAM_GB = 2.0
# Minimum total RAM (GB) needed for SmolVLM on CPU
SMOLVLM_MIN_RAM_GB = 4.0
# Low-memory guardrail where SmolVLM is preferred over moondream2
SMOLVLM_PREFERRED_MAX_AVAILABLE_RAM_GB = 1.5
# Maximum RAM the VLM should use (to stay within 8GB total)
VLM_MAX_RAM_GB = float(os.getenv("VLM_MAX_RAM_GB", "5.0"))

# ─── VLM Inference Settings ────────────────────────────────────────────────
VLM_MAX_NEW_TOKENS = 300
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

VLM_JUDGE_PROMPT = """You are an ULTRA-STRICT facial authentication security system. Your #1 job is to REJECT spoofing attacks. Be extremely suspicious and paranoid.

TASK: Analyze the provided images VERY carefully using the following strict 3-stage pipeline.
- The FIRST image(s) are from the user's REGISTRATION (reference identity).
- The LAST image(s) are from the current AUTHENTICATION attempt.

═══════════════════════════════════════════════════════════════
STAGE 1 — DEVICE / MEDIA DETECTION (CRITICAL — check this FIRST)
═══════════════════════════════════════════════════════════════
Before doing ANYTHING else, carefully scan the AUTHENTICATION image(s) for ANY of these:
  • A mobile phone, smartphone, or tablet being held up to the camera
  • A laptop screen, monitor, TV, or any electronic display
  • A printed photograph or paper being held up
  • A picture frame or poster containing a face
  • A video playing on any device
  • Any rectangular glowing screen edge, bezel, or device frame visible
  • Fingers or hands holding a device that displays a face
  • A face that appears INSIDE a smaller rectangular region (screen-within-a-frame)
  • Moiré patterns, pixel grids, or scan lines from a digital screen
  • Reflections on glass/screen surface overlapping the face

IF YOU DETECT ANY DEVICE OR MEDIA: immediately set is_live=false, is_authentic=false, liveness_confidence ≤ 0.1, authenticity_confidence ≤ 0.1, overall_score ≤ 0.1. This is a SPOOFING ATTACK. Do NOT proceed to identity matching.

═══════════════════════════════════════════════════════════════
STAGE 2 — REAL FACE IN FULL FRAME VERIFICATION
═══════════════════════════════════════════════════════════════
ONLY if Stage 1 passes (no device detected), check:
  • The face must fill the frame NATURALLY — like a person sitting in front of a webcam
  • There must be visible 3D depth cues: natural shadow gradients under the nose, chin, and eye sockets; visible ear(s) receding in perspective; neck and shoulders visible below the face
  • Skin must show natural texture: pores, fine lines, micro-imperfections, natural color variations
  • Background should look like a real room environment (walls, furniture, etc.) — NOT a flat/uniform background from a screen capture
  • Lighting on the face must be consistent with the visible environment and show natural falloff
  • Check for flat, poster-like appearance that indicates a 2D surface

═══════════════════════════════════════════════════════════════
STAGE 3 — EYE BLINK & LIVENESS CROSS-FRAME CHECK
═══════════════════════════════════════════════════════════════
Compare across the authentication frame(s):
  • Are the person's eyes in DIFFERENT states across frames? (e.g., open in one, mid-blink or closed in another) — this is STRONG evidence of liveness
  • If eyes are in the EXACT same position and openness across ALL frames, this is suspicious — a photo or static replay will have identical eye states
  • Look for any subtle expression micro-changes between frames (real people have involuntary micro-movements)
  • Check for natural specular highlights in the eyes that shift position between frames (real 3D eyes reflect light differently as the person micro-moves)
  • If ONLY one frame is available: look for natural blink-related features — are the eyes at a natural openness, or frozen wide-open like a photo?

═══════════════════════════════════════════════════════════════
STAGE 4 — IDENTITY MATCH (only if Stages 1-3 pass)
═══════════════════════════════════════════════════════════════
  • Compare the REGISTRATION face with the AUTHENTICATION face
  • Check: facial bone structure, nose shape, eye spacing, eyebrow shape, jawline, ear shape, unique marks (moles, scars, freckles)
  • Account for: different lighting, slight angle changes, natural expression variation
  • Be strict: if facial structure differs significantly, set same_person=false

CRITICAL RULES:
  1. When in DOUBT, always DENY. False rejection is better than false acceptance.
  2. If you see ANY phone, screen, or printed media → automatic DENY, overall_score ≤ 0.1
  3. A real live person MUST show natural 3D depth, skin texture, and environmental context
  4. If eyes are identical/frozen across multiple frames → strongly suspect a photo/video replay

Respond ONLY with a valid JSON object (no extra text before or after):
{
  "same_person": true or false,
  "same_person_confidence": 0.0 to 1.0,
  "is_live": true or false,
  "liveness_confidence": 0.0 to 1.0,
  "is_authentic": true or false,
  "authenticity_confidence": 0.0 to 1.0,
  "overall_score": 0.0 to 1.0,
  "reasoning": "Describe what you see step-by-step: Stage 1 (device check), Stage 2 (face quality), Stage 3 (blink/liveness), Stage 4 (identity). Be specific about what evidence you found.",
  "red_flags": ["list every concern found, or empty list if truly none"]
}"""

VLM_JUDGE_PROMPT_SIMPLE = """You are a STRICT anti-spoofing face authentication system. Analyze these images carefully.

The FIRST image = registered user. The LAST image = authentication attempt.

CHECK IN THIS ORDER:
1. DEVICE CHECK: Is there ANY mobile phone, tablet, laptop screen, printed photo, or video display visible in the authentication image? If YES → is_live=false, is_authentic=false, overall_score=0.05. This is a spoofing attack.
2. FACE CHECK: Does the face fill the frame naturally like a real person at a webcam? Look for 3D depth (shadows under nose/chin), real skin texture (pores, imperfections), real environment behind them. A flat, screen-like, or paper-like appearance = DENY.
3. BLINK CHECK: Compare eye states across frames. If eyes are frozen/identical = suspicious (photo or static replay). Different eye states across frames = evidence of real liveness.
4. IDENTITY: Same person in registration and auth images?

When in doubt, DENY. A phone showing a face is NOT a real person.

Respond ONLY in JSON:
{
  "same_person": true/false,
  "same_person_confidence": 0.0-1.0,
  "is_live": true/false,
  "liveness_confidence": 0.0-1.0,
  "is_authentic": true/false,
  "authenticity_confidence": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "reasoning": "step-by-step: device check result, face check result, blink check result, identity result",
  "red_flags": []
}"""

VLM_STRICT_ANTI_SPOOF_APPENDIX = """

NON-NEGOTIABLE AUTHENTICATION POLICY FOR BOTH HYBRID AND PURE VLM MODES:
- Grant access ONLY when the authentication frames show the real user directly in the camera view.
- The live user's face must be the main full-frame subject. If a mobile phone, tablet, laptop, monitor, TV, printed photo, picture, poster, replayed video, or any secondary displayed face is visible anywhere in the authentication frames, treat it as a presentation attack and DENY.
- If a face appears inside another rectangle, device screen, bezel, playback window, gallery image, or reflected display, DENY even if the face resembles the registered user.
- If the user's face is blocked, cropped, partially hidden, or covered by a phone or other device, DENY. Access is allowed only when the full face is clearly visible in the main camera frame.
- Compare the authentication frames for eye-state changes. Natural blink evidence means the eyes should not look frozen in exactly the same state across all auth frames. If the eyes remain identical or frozen across the frames, treat that as negative liveness evidence and keep liveness low.
- If you are uncertain whether the user is live, whether a device is present, or whether the full face is visible, DENY.
- If any presentation attack evidence exists, set same_person=false, is_live=false, is_authentic=false, same_person_confidence<=0.10, liveness_confidence<=0.10, authenticity_confidence<=0.10, and overall_score<=0.05.
- The overall_score is the final authentication trust score, not the confidence of your explanation. If is_live=false or is_authentic=false, overall_score must stay low.
- Include explicit red flags when relevant, choosing from: visible_mobile_phone, visible_tablet, visible_laptop_screen, visible_monitor_or_tv, printed_photo, picture_or_poster, replayed_video, screen_bezel_or_edges, face_inside_secondary_rectangle, frozen_eye_state, full_face_not_visible, face_occluded_by_device.
- Respond with JSON only. Do not add markdown, prose outside JSON, or extra commentary.
"""

VLM_JUDGE_PROMPT += VLM_STRICT_ANTI_SPOOF_APPENDIX
VLM_JUDGE_PROMPT_SIMPLE += VLM_STRICT_ANTI_SPOOF_APPENDIX


def detect_available_hardware():
    """Detect GPU/CPU capabilities for model selection."""
    info = {
        "cuda_available": False,
        "gpu_name": None,
        "vram_gb": 0.0,
        "ram_gb": 8.0,
        "ram_available_gb": 4.0,
    }

    try:
        import psutil
        info["ram_gb"] = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        info["ram_available_gb"] = round(psutil.virtual_memory().available / (1024 ** 3), 1)
    except ImportError:
        logger.warning("psutil not installed — assuming 8GB RAM")
    except Exception:
        pass

    try:
        import torch
        if torch.cuda.is_available():
            info["cuda_available"] = True
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["vram_gb"] = round(
                torch.cuda.get_device_properties(0).total_mem / (1024 ** 3), 1
            )
    except ImportError:
        logger.warning("torch not installed — assuming CPU only")
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

    if VLM_MODEL_OVERRIDE == "smolvlm":
        device = "cuda" if hw["cuda_available"] else "cpu"
        logger.info(f"VLM: Using SmolVLM-256M-Instruct (forced, {device})")
        return SMOLVLM_MODEL_ID, "bf16", device

    # Auto selection
    # Priority 1: Qwen on GPU (best accuracy)
    if hw["cuda_available"] and hw["vram_gb"] >= QWEN_MIN_VRAM_GB:
        logger.info("VLM auto-selected: Qwen2.5-VL-3B-Instruct (4-bit, CUDA)")
        return QWEN_MODEL_ID, "4bit", "cuda"

    # Priority 2: moondream2 on CPU when there is enough headroom.
    if (
        hw["ram_gb"] >= MOONDREAM_MIN_RAM_GB
        and hw["ram_available_gb"] >= MOONDREAM_RECOMMENDED_AVAILABLE_RAM_GB
    ):
        device = "cuda" if hw["cuda_available"] else "cpu"
        logger.info(f"VLM auto-selected: moondream2 ({device})")
        return MOONDREAM_MODEL_ID, "fp16", device

    # Priority 3: lightweight CPU fallback for low-memory Windows machines.
    if hw["ram_gb"] >= SMOLVLM_MIN_RAM_GB:
        device = "cuda" if hw["cuda_available"] else "cpu"
        if hw["ram_available_gb"] <= SMOLVLM_PREFERRED_MAX_AVAILABLE_RAM_GB:
            logger.warning(
                "VLM auto-selected: SmolVLM-256M-Instruct (%s) because available RAM "
                "is only %.1fGB. This avoids moondream2 paging-file failures.",
                device,
                hw["ram_available_gb"],
            )
        else:
            logger.info(f"VLM auto-selected: SmolVLM-256M-Instruct ({device})")
        return SMOLVLM_MODEL_ID, "bf16", device

    # Fallback for borderline systems that already have moondream cached locally.
    moondream_cache_dir = VLM_CACHE_DIR / "models--vikhyatk--moondream2"
    if moondream_cache_dir.exists():
        device = "cuda" if hw["cuda_available"] else "cpu"
        logger.info(f"VLM auto-selected from cache: moondream2 ({device})")
        return MOONDREAM_MODEL_ID, "fp16", device

    # Not enough resources
    logger.warning(
        f"VLM: Insufficient resources (VRAM={hw['vram_gb']}GB, "
        f"RAM_total={hw['ram_gb']}GB, RAM_avail={hw['ram_available_gb']}GB). VLM disabled."
    )
    return None, None, None
