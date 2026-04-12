"""
vlm_reasoner.py — Vision Language Model reasoning for facial authentication.

This module provides the VLM "Judge" layer that performs semantic visual
reasoning on face images. It supports two models with auto-fallback:

  1. Qwen2.5-VL-3B-Instruct — best accuracy, needs GPU + 4-bit quantization
  2. moondream2 (1.9B) — lightweight, works on CPU with 8GB RAM

The VLM receives registration reference frame(s) and authentication frame(s),
then produces a structured judgment about identity match, liveness, and
authenticity with natural language reasoning.

This module is ADDITIVE — does not modify any existing model files.
"""

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class VLMJudgment:
    """Result from VLM reasoning about a face authentication attempt."""
    same_person: bool = False
    same_person_confidence: float = 0.0
    is_live: bool = False
    liveness_confidence: float = 0.0
    is_authentic: bool = False
    authenticity_confidence: float = 0.0
    overall_score: float = 0.0
    reasoning: str = ""
    red_flags: list[str] = field(default_factory=list)
    model_used: str = "none"
    inference_time_ms: float = 0.0
    error: Optional[str] = None


def _neutral_judgment(reason: str = "VLM not available") -> VLMJudgment:
    """Return a neutral judgment that doesn't affect the traditional pipeline."""
    return VLMJudgment(
        same_person=True,
        same_person_confidence=0.5,
        is_live=True,
        liveness_confidence=0.5,
        is_authentic=True,
        authenticity_confidence=0.5,
        overall_score=0.5,
        reasoning=f"VLM analysis skipped: {reason}",
        red_flags=[],
        model_used="none",
        error=reason,
    )


def _bgr_to_pil(frame_bgr: np.ndarray, max_size: int = 384) -> Image.Image:
    """Convert BGR numpy array to PIL Image, resized for VLM input."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)

    # Resize to keep VLM input manageable
    w, h = pil_img.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        pil_img = pil_img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    return pil_img


def _parse_vlm_json(text: str) -> dict:
    """
    Extract JSON from VLM output, handling various formats.
    VLMs may wrap JSON in markdown code blocks or add extra text.
    """
    # Try direct JSON parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding any JSON object in the text
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Last resort: extract key values with regex
    result = {
        "same_person": True,
        "same_person_confidence": 0.5,
        "is_live": True,
        "liveness_confidence": 0.5,
        "is_authentic": True,
        "authenticity_confidence": 0.5,
        "overall_score": 0.5,
        "reasoning": text[:500],
        "red_flags": [],
    }

    # Try to extract boolean values
    for key in ["same_person", "is_live", "is_authentic"]:
        match = re.search(
            rf'"{key}"\s*:\s*(?:"(?P<quoted>true|false)"|(?P<plain>true|false))',
            text,
            re.IGNORECASE,
        )
        if match:
            token = match.group("quoted") or match.group("plain")
            coerced = _coerce_bool(token)
            if coerced is not None:
                result[key] = coerced

    # Try to extract float values
    for key in ["same_person_confidence", "liveness_confidence",
                 "authenticity_confidence", "overall_score"]:
        match = re.search(
            rf'"{key}"\s*:\s*(?:"(?P<quoted>[^"]+)"|(?P<plain>[^,\n}}]+))',
            text,
            re.IGNORECASE,
        )
        if match:
            token = (match.group("quoted") or match.group("plain") or "").strip()
            coerced = _coerce_score(token)
            if coerced is not None:
                result[key] = coerced

    return result


def _normalize_moondream_output(output) -> str:
    """Normalize moondream responses across old and new API variants."""
    if isinstance(output, str):
        return output

    if isinstance(output, dict):
        for key in ("answer", "response", "text", "caption"):
            value = output.get(key)
            if isinstance(value, str) and value.strip():
                return value
        try:
            return json.dumps(output)
        except Exception:
            return str(output)

    return str(output)


def _coerce_bool(value) -> Optional[bool]:
    """Coerce bool-like JSON/string values into Python booleans."""
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)

    if isinstance(value, str):
        lowered = value.strip().strip('"').strip("'").lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False

    return None


def _coerce_score(value) -> Optional[float]:
    """Parse numeric strings conservatively and reject placeholder ranges."""
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        try:
            score = float(value)
        except (TypeError, ValueError):
            return None
        if np.isnan(score) or np.isinf(score):
            return None
        return float(np.clip(score, 0.0, 1.0))

    if isinstance(value, str):
        cleaned = value.strip().strip('"').strip("'")
        if not cleaned:
            return None
        if "-" in cleaned:
            return None
        if not re.fullmatch(r"\d+(?:\.\d+)?", cleaned):
            return None
        score = float(cleaned)
        return float(np.clip(score, 0.0, 1.0))

    return None


def _find_first_nested_value(data, target_key: str):
    """Recursively find the first matching key value in nested dict/list data."""
    if isinstance(data, dict):
        if target_key in data and not isinstance(data[target_key], (dict, list)):
            return data[target_key]
        for value in data.values():
            found = _find_first_nested_value(value, target_key)
            if found is not None:
                return found

    if isinstance(data, list):
        for item in data:
            found = _find_first_nested_value(item, target_key)
            if found is not None:
                return found

    return None


def _flatten_nested_vlm_output(parsed: dict) -> dict:
    """Flatten malformed nested JSON into the expected top-level schema."""
    if not isinstance(parsed, dict):
        return {"_schema_malformed": True}

    schema_keys = (
        "same_person",
        "same_person_confidence",
        "is_live",
        "liveness_confidence",
        "is_authentic",
        "authenticity_confidence",
        "overall_score",
        "reasoning",
        "red_flags",
    )

    flattened: dict = {"_schema_malformed": False}

    for key in schema_keys:
        value = parsed.get(key)
        if isinstance(value, dict):
            flattened["_schema_malformed"] = True
        elif value is not None:
            flattened[key] = value
            continue

        nested_value = _find_first_nested_value(parsed, key)
        if nested_value is not None:
            flattened[key] = nested_value

    red_flags = flattened.get("red_flags")
    if red_flags is None:
        red_flags = []
    if not isinstance(red_flags, list):
        red_flags = [str(red_flags)]
    flattened["red_flags"] = [str(flag).strip() for flag in red_flags if str(flag).strip()]

    return flattened


def _looks_like_schema_echo(text: str) -> bool:
    """Detect placeholder/schema echo output from weaker VLMs."""
    lowered = (text or "").lower()
    if not lowered:
        return False

    echo_markers = (
        '"same_person": {',
        "0.0-1.0",
        "true/false",
        "return exactly this schema",
        "respond only in json",
        "use real decimal numbers",
    )
    return any(marker in lowered for marker in echo_markers)


def _infer_boolean_signal(
    text: str,
    positive_terms: list[str],
    negative_terms: list[str],
    neutral_confidence: float,
) -> tuple[Optional[bool], float]:
    """Infer a boolean signal and a fallback confidence from free-form text."""
    lowered = text.lower()

    if any(term in lowered for term in negative_terms):
        return False, 0.2

    if any(term in lowered for term in positive_terms):
        return True, 0.8

    return None, neutral_confidence


def _clamp_score(value, default: float) -> float:
    """Clamp a parsed score into [0, 1], with a default when parsing fails."""
    score = _coerce_score(value)
    if score is None:
        return default
    return score


def _merge_red_flags(existing: list[str], additions: list[str]) -> list[str]:
    """Merge red flags while preserving order and uniqueness."""
    merged: list[str] = []
    for flag in list(existing) + list(additions):
        normalized = str(flag).strip()
        if normalized and normalized not in merged:
            merged.append(normalized)
    return merged


def _red_flags_contain(red_flags: list[str], *targets: str) -> bool:
    """Return True when any target red flag is present."""
    red_flag_set = {str(flag).strip() for flag in red_flags}
    return any(target in red_flag_set for target in targets)


def _apply_security_overrides(
    *,
    same_person: bool,
    same_person_confidence: float,
    is_live: bool,
    liveness_confidence: float,
    is_authentic: bool,
    authenticity_confidence: float,
    overall_score: float,
    reasoning: str,
    red_flags: list[str],
    raw_output: str,
    schema_malformed: bool,
) -> dict:
    """Apply conservative score caps when spoof evidence or malformed schema appears."""
    reasoning = (reasoning or "").strip()
    evidence_text = " ".join(
        [
            raw_output or "",
            reasoning,
            " ".join(red_flags or []),
        ]
    ).lower()

    detected_flags: list[str] = []
    severity = 0

    rule_map = [
        (("mobile phone", "smartphone", "cell phone", "phone screen", "mobile screen", "phone display"), "visible_mobile_phone", 3),
        (("tablet", "ipad"), "visible_tablet", 3),
        (("laptop screen", "laptop display", "notebook screen", "laptop"), "visible_laptop_screen", 3),
        (("monitor", "tv screen", "television", "display screen", "electronic display"), "visible_monitor_or_tv", 3),
        (("printed photo", "paper photo", "hard copy", "hardcopy", "paper face", "photo id", "identity card", "id card", "passport photo", "document photo"), "printed_photo", 3),
        (("poster", "picture", "portrait photo", "framed photo", "portrait print"), "picture_or_poster", 2),
        (("replayed video", "video playing", "video replay", "playing video", "recorded clip", "recorded video", "gallery video"), "replayed_video", 3),
        (("screen edge", "bezel", "glowing edge", "device frame", "screen border", "black border"), "screen_bezel_or_edges", 2),
        (("secondary rectangle", "inside another rectangle", "screen-within-a-frame", "face inside another rectangle", "playback window", "gallery image"), "face_inside_secondary_rectangle", 3),
        (("full face not visible", "partial face", "partially hidden", "cropped face", "face cut off", "not full face"), "full_face_not_visible", 2),
        (("occluded by device", "covered by phone", "blocked by phone", "covered by device", "held in front of the face", "covering part of face"), "face_occluded_by_device", 3),
        (("frozen eyes", "identical eye", "same eye state", "no blink", "frozen eye state"), "frozen_eye_state", 2),
    ]

    for terms, flag, points in rule_map:
        if any(term in evidence_text for term in terms):
            detected_flags.append(flag)
            severity += points

    if (
        any(
            term in evidence_text
            for term in (
                "holding a",
                "held up",
                "hands holding",
                "fingers holding",
                "holding device",
                "hand visible",
                "hands visible",
                "fingers visible",
            )
        )
        and any(
            flag in detected_flags
            for flag in (
                "visible_mobile_phone",
                "visible_tablet",
                "visible_laptop_screen",
                "visible_monitor_or_tv",
                "printed_photo",
                "picture_or_poster",
            )
        )
    ):
        detected_flags.append("face_occluded_by_device")
        severity += 2

    if schema_malformed:
        detected_flags.append("invalid_vlm_schema_output")

    red_flags = _merge_red_flags(red_flags, detected_flags)

    device_attack = _red_flags_contain(
        red_flags,
        "visible_mobile_phone",
        "visible_tablet",
        "visible_laptop_screen",
        "visible_monitor_or_tv",
        "printed_photo",
        "picture_or_poster",
        "replayed_video",
        "screen_bezel_or_edges",
        "face_inside_secondary_rectangle",
        "face_occluded_by_device",
        "full_face_not_visible",
    )
    frozen_eye_state = _red_flags_contain(red_flags, "frozen_eye_state")

    if device_attack:
        same_person = False
        is_live = False
        is_authentic = False

        if severity >= 6:
            same_person_confidence = min(same_person_confidence, 0.20)
            liveness_confidence = min(liveness_confidence, 0.05)
            authenticity_confidence = min(authenticity_confidence, 0.05)
            overall_score = min(overall_score, 0.05)
        elif severity >= 3:
            same_person_confidence = min(same_person_confidence, 0.30)
            liveness_confidence = min(liveness_confidence, 0.10)
            authenticity_confidence = min(authenticity_confidence, 0.10)
            overall_score = min(overall_score, 0.10)
        else:
            same_person_confidence = min(same_person_confidence, 0.45)
            liveness_confidence = min(liveness_confidence, 0.20)
            authenticity_confidence = min(authenticity_confidence, 0.20)
            overall_score = min(overall_score, 0.20)

        if "faking" not in reasoning.lower():
            spoof_note = (
                "Authentication frames indicate the user is likely faking the login with a screen, device, photo, or replayed media."
            )
            reasoning = f"{reasoning} {spoof_note}".strip() if reasoning else spoof_note

    if frozen_eye_state and not device_attack:
        is_live = False
        liveness_confidence = min(liveness_confidence, 0.25)
        overall_score = min(overall_score, 0.35)
        if "blink" not in reasoning.lower():
            blink_note = "Authentication frames show frozen or identical eye states with weak blink evidence."
            reasoning = f"{reasoning} {blink_note}".strip() if reasoning else blink_note

    if schema_malformed and not device_attack:
        same_person_confidence = min(same_person_confidence, 0.45)
        liveness_confidence = min(liveness_confidence, 0.35)
        authenticity_confidence = min(authenticity_confidence, 0.35)
        overall_score = min(overall_score, 0.35)
        if "malformed" not in reasoning.lower():
            malformed_note = (
                "The VLM returned malformed schema output, so a conservative post-processing fallback was applied."
            )
            reasoning = f"{reasoning} {malformed_note}".strip() if reasoning else malformed_note

    if not is_authentic:
        overall_score = min(overall_score, 0.30)

    return {
        "same_person": same_person,
        "same_person_confidence": same_person_confidence,
        "is_live": is_live,
        "liveness_confidence": liveness_confidence,
        "is_authentic": is_authentic,
        "authenticity_confidence": authenticity_confidence,
        "overall_score": overall_score,
        "reasoning": reasoning,
        "red_flags": red_flags,
    }


def _normalize_parsed_vlm_output(parsed: dict, raw_output: str) -> dict:
    """Fill missing confidence values when the model answers in natural language."""
    parsed = _flatten_nested_vlm_output(parsed)
    schema_malformed = bool(parsed.pop("_schema_malformed", False))
    raw_output_lower = (raw_output or "").lower()

    reasoning_text = str(parsed.get("reasoning", "")).strip()
    heuristic_text = reasoning_text if reasoning_text and not _looks_like_schema_echo(reasoning_text) else ""
    if not heuristic_text and not schema_malformed and not _looks_like_schema_echo(raw_output):
        heuristic_text = raw_output

    same_person_signal, same_person_fallback = _infer_boolean_signal(
        heuristic_text,
        positive_terms=[
            "same person",
            "same individual",
            "same identity",
            "appear to match",
            "appear to be the same",
        ],
        negative_terms=[
            "different person",
            "identity mismatch",
            "not the same person",
            "do not match",
        ],
        neutral_confidence=0.55,
    )
    live_signal, live_fallback = _infer_boolean_signal(
        heuristic_text,
        positive_terms=[
            "live person",
            "real person",
            "appears live",
            "looks live",
            "blink detected",
            "eyes are different",
            "natural micro-movement",
            "natural movement",
        ],
        negative_terms=[
            "not live",
            "photo",
            "printed",
            "screen replay",
            "replay attack",
            "phone",
            "mobile",
            "smartphone",
            "phone gallery",
            "phone video",
            "tablet",
            "device",
            "screen",
            "display",
            "monitor",
            "laptop",
            "photo id",
            "identity card",
            "id card",
            "bezel",
            "held up",
            "holding a",
            "video replay",
            "video playing",
            "recorded clip",
            "recorded video",
            "no blink",
            "frozen eyes",
            "identical eye",
            "same eye state",
            "no micro-movement",
            "static",
            "flat appearance",
            "2d surface",
            "pixel grid",
            "scan lines",
            "spoofing",
            "spoof",
        ],
        neutral_confidence=0.6,
    )
    authentic_signal, authentic_fallback = _infer_boolean_signal(
        heuristic_text,
        positive_terms=[
            "authentic",
            "looks authentic",
            "appears real",
            "genuine face",
            "real face",
            "natural 3d",
            "natural depth",
        ],
        negative_terms=[
            "deepfake",
            "spoof",
            "manipulated",
            "synthetic",
            "fake",
            "phone screen",
            "device screen",
            "phone gallery",
            "phone video",
            "displayed on",
            "shown on",
            "projected",
            "screen-within",
            "rectangular region",
            "electronic display",
            "presentation attack",
            "print attack",
            "photo id",
            "identity card",
            "id card",
            "mask",
            "paper",
            "flat image",
        ],
        neutral_confidence=0.6,
    )

    same_person_value = _coerce_bool(parsed.get("same_person"))
    live_value = _coerce_bool(parsed.get("is_live"))
    authentic_value = _coerce_bool(parsed.get("is_authentic"))

    same_person = (
        same_person_value
        if same_person_value is not None
        else same_person_signal
        if same_person_signal is not None
        else False if schema_malformed else True
    )
    is_live = (
        live_value
        if live_value is not None
        else live_signal
        if live_signal is not None
        else False if schema_malformed else True
    )
    is_authentic = (
        authentic_value
        if authentic_value is not None
        else authentic_signal
        if authentic_signal is not None
        else False if schema_malformed else True
    )

    same_person_confidence = _clamp_score(parsed.get("same_person_confidence"), default=0.0)
    liveness_confidence = _clamp_score(parsed.get("liveness_confidence"), default=0.0)
    authenticity_confidence = _clamp_score(parsed.get("authenticity_confidence"), default=0.0)

    if (
        same_person_confidence <= 0.0
        or (
            same_person_confidence == 0.5
            and "same_person_confidence" not in raw_output_lower
        )
    ):
        same_person_confidence = (
            same_person_fallback if same_person else 1.0 - same_person_fallback
        )
    if (
        liveness_confidence <= 0.0
        or (
            liveness_confidence == 0.5
            and "liveness_confidence" not in raw_output_lower
        )
    ):
        liveness_confidence = live_fallback if is_live else 1.0 - live_fallback
    if (
        authenticity_confidence <= 0.0
        or (
            authenticity_confidence == 0.5
            and "authenticity_confidence" not in raw_output_lower
        )
    ):
        authenticity_confidence = (
            authentic_fallback if is_authentic else 1.0 - authentic_fallback
        )

    overall_score = _clamp_score(parsed.get("overall_score"), default=0.0)
    if overall_score <= 0.0 or (overall_score == 0.5 and "overall_score" not in raw_output_lower):
        overall_score = float(
            np.mean([
                same_person_confidence,
                liveness_confidence,
                authenticity_confidence,
            ])
        )

    red_flags = parsed.get("red_flags", [])
    if not isinstance(red_flags, list):
        red_flags = []

    reasoning = reasoning_text
    if not reasoning or reasoning.startswith("{") and reasoning.endswith("}"):
        reasoning = _build_reasoning_summary(
            same_person=same_person,
            same_person_confidence=same_person_confidence,
            is_live=is_live,
            liveness_confidence=liveness_confidence,
            is_authentic=is_authentic,
            authenticity_confidence=authenticity_confidence,
            overall_score=overall_score,
            red_flags=red_flags,
        )

    secured = _apply_security_overrides(
        same_person=same_person,
        same_person_confidence=same_person_confidence,
        is_live=is_live,
        liveness_confidence=liveness_confidence,
        is_authentic=is_authentic,
        authenticity_confidence=authenticity_confidence,
        overall_score=overall_score,
        reasoning=reasoning,
        red_flags=red_flags,
        raw_output=raw_output,
        schema_malformed=schema_malformed,
    )

    return {
        "same_person": bool(secured["same_person"]),
        "same_person_confidence": float(np.clip(secured["same_person_confidence"], 0.0, 1.0)),
        "is_live": bool(secured["is_live"]),
        "liveness_confidence": float(np.clip(secured["liveness_confidence"], 0.0, 1.0)),
        "is_authentic": bool(secured["is_authentic"]),
        "authenticity_confidence": float(np.clip(secured["authenticity_confidence"], 0.0, 1.0)),
        "overall_score": float(np.clip(secured["overall_score"], 0.0, 1.0)),
        "reasoning": str(secured["reasoning"]).strip(),
        "red_flags": list(secured["red_flags"]),
    }


def _build_reasoning_summary(
    same_person: bool,
    same_person_confidence: float,
    is_live: bool,
    liveness_confidence: float,
    is_authentic: bool,
    authenticity_confidence: float,
    overall_score: float,
    red_flags: list[str],
) -> str:
    """Build a readable fallback explanation when the model omits reasoning."""
    reg_summary = (
        "Registration reference summary: stored registration frames are treated as the baseline for stable facial structure."
    )
    auth_summary = (
        "Authentication frame summary: current login frames were checked for device spoofing, screen boundaries, full-face visibility, blink evidence, and natural motion."
    )

    if _red_flags_contain(
        red_flags,
        "visible_mobile_phone",
        "visible_tablet",
        "visible_laptop_screen",
        "visible_monitor_or_tv",
        "printed_photo",
        "picture_or_poster",
        "replayed_video",
        "screen_bezel_or_edges",
        "face_inside_secondary_rectangle",
        "face_occluded_by_device",
    ):
        device_summary = (
            "Device and screen analysis: the authentication frames indicate spoof evidence consistent with a phone, screen, printed image, or replayed media attack."
        )
    else:
        device_summary = (
            "Device and screen analysis: no strong phone, screen, or printed-media evidence was inferred from the available output."
        )

    if _red_flags_contain(red_flags, "frozen_eye_state"):
        blink_summary = (
            f"Eye blink and motion analysis: blink evidence is weak and the eye state appears frozen across frames, so liveness remains low at {liveness_confidence:.0%}."
        )
    else:
        blink_summary = (
            f"Eye blink and motion analysis: liveness {'passes' if is_live else 'fails'} with confidence {liveness_confidence:.0%}."
        )

    identity_summary = (
        f"Identity comparison: the authentication face {'matches' if same_person else 'does not match'} the registration reference frames with confidence {same_person_confidence:.0%}."
    )
    verdict_summary = (
        f"Final verdict: authenticity {'passes' if is_authentic else 'fails'} at {authenticity_confidence:.0%}, and the overall authentication score is {overall_score:.0%}."
    )

    summary = " ".join(
        [
            reg_summary,
            auth_summary,
            device_summary,
            blink_summary,
            identity_summary,
            verdict_summary,
        ]
    )
    if red_flags:
        summary += f" Red flags: {', '.join(red_flags)}."

    return summary


class VLMReasoner:
    """
    VLM-based facial authentication reasoner.

    Supports:
      - Qwen2.5-VL-3B-Instruct (GPU, 4-bit quantized)
      - moondream2 (CPU/GPU, fp16)

    Uses lazy loading — model is loaded on first inference call.
    """

    def __init__(self):
        self.model = None
        self.processor = None
        self.tokenizer = None
        self.model_id = None
        self.model_name = "none"
        self.device = "cpu"
        self.loaded = False
        self._load_attempted = False
        self.load_error = None
        self._load_lock = threading.RLock()
        self._infer_lock = threading.RLock()

    def _load_model(self):
        """Lazy-load the VLM model based on available hardware. Auto-downloads if needed."""
        with self._load_lock:
            if self._load_attempted:
                return

            from app.vlm_config import (
                MOONDREAM_MODEL_ID,
                SMOLVLM_MODEL_ID,
                VLM_CACHE_DIR,
                detect_available_hardware,
                select_vlm_model,
            )

            model_id, quantize, device = select_vlm_model()

            if model_id is None:
                logger.warning("VLM: No suitable model found - VLM reasoning disabled")
                self.load_error = "No suitable VLM model found for this hardware"
                self._load_attempted = True
                return

            hw = detect_available_hardware()
            candidates: list[tuple[str, str, str]] = [(model_id, quantize, device)]

            if "qwen" in model_id.lower():
                fb_device = "cuda" if hw["cuda_available"] else "cpu"
                candidates.append((MOONDREAM_MODEL_ID, "fp16", fb_device))
                candidates.append((SMOLVLM_MODEL_ID, "bf16", fb_device))
            elif "moondream" in model_id.lower():
                candidates.append(
                    (SMOLVLM_MODEL_ID, "bf16", "cuda" if hw["cuda_available"] else "cpu")
                )

            for candidate_id, candidate_quantize, candidate_device in candidates:
                self.model = None
                self.processor = None
                self.tokenizer = None
                self.model_id = candidate_id
                self.device = candidate_device
                self.model_name = "none"
                self.loaded = False
                self.load_error = None

                try:
                    logger.info(
                        "VLM: Loading %s (quantize=%s, device=%s). Cache dir: %s",
                        candidate_id,
                        candidate_quantize,
                        candidate_device,
                        VLM_CACHE_DIR,
                    )

                    if "qwen" in candidate_id.lower():
                        self._load_qwen(candidate_id, candidate_quantize, candidate_device)
                    elif "moondream" in candidate_id.lower():
                        self._load_moondream(candidate_id, candidate_device)
                    elif "smolvlm" in candidate_id.lower():
                        self._load_smolvlm(candidate_id, candidate_device)
                    else:
                        raise ValueError(f"Unknown VLM model ID: {candidate_id}")

                    self.loaded = True
                    self._load_attempted = True
                    logger.info("VLM loaded successfully: %s on %s", self.model_name, self.device)
                    return

                except Exception as exc:
                    self.load_error = str(exc)
                    logger.error("VLM load failed (%s): %s", candidate_id, exc, exc_info=True)
                    continue

            self._load_attempted = True

    def ensure_loaded(self) -> dict:
        """Force a lazy model load and return the resulting status."""
        if not self.loaded:
            self._load_model()
        return self.get_status()

    @staticmethod
    def _configure_torch_cpu_runtime():
        """Clamp CPU threading to reduce memory spikes on Windows."""
        try:
            import torch

            torch.set_num_threads(1)
            if hasattr(torch, "set_num_interop_threads"):
                torch.set_num_interop_threads(1)
        except Exception:
            pass

    def _load_qwen(self, model_id: str, quantize: str, device: str):
        """Load Qwen2.5-VL-3B-Instruct with 4-bit quantization."""
        import torch
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
        from app.vlm_config import VLM_CACHE_DIR

        logger.info(f"Loading Qwen2.5-VL ({quantize}) on {device}...")

        load_kwargs = {
            "cache_dir": str(VLM_CACHE_DIR),
            "trust_remote_code": True,
            "dtype": torch.float16,
        }

        if quantize == "4bit" and device == "cuda":
            try:
                from transformers import BitsAndBytesConfig
                load_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                )
                load_kwargs["device_map"] = "auto"
            except ImportError:
                logger.warning("bitsandbytes not available — loading Qwen in fp16")
                load_kwargs["device_map"] = "auto"
        else:
            load_kwargs["device_map"] = "auto"

        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            model_id, **load_kwargs
        )
        self.processor = AutoProcessor.from_pretrained(
            model_id,
            cache_dir=str(VLM_CACHE_DIR),
            trust_remote_code=True,
        )
        self.model_name = "qwen2.5-vl-3b"
        self.device = device

    def _load_moondream(self, model_id: str, device: str):
        """Load moondream2 model. Auto-downloads ~3.6GB on first run."""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from app.vlm_config import VLM_CACHE_DIR, MOONDREAM_MODEL_REVISION

        logger.info(
            "Loading moondream2 on %s using revision %s...",
            device,
            MOONDREAM_MODEL_REVISION,
        )

        load_kwargs = {
            "cache_dir": str(VLM_CACHE_DIR),
            "trust_remote_code": True,
            "revision": MOONDREAM_MODEL_REVISION,
            "low_cpu_mem_usage": True,
        }
        if device == "cuda":
            load_kwargs["dtype"] = torch.float16
            load_kwargs["device_map"] = {"": "cuda"}
        else:
            self._configure_torch_cpu_runtime()
            # Keep CPU memory usage lower by respecting the model's native dtype.
            load_kwargs["dtype"] = "auto"
            load_kwargs["device_map"] = {"": "cpu"}
            load_kwargs["attn_implementation"] = "eager"

        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            **load_kwargs,
        )
        self.model.eval()

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            cache_dir=str(VLM_CACHE_DIR),
            trust_remote_code=True,
            revision=MOONDREAM_MODEL_REVISION,
        )
        self.model_name = "moondream2"
        self.device = device
        logger.info("moondream2 model loaded successfully")

    def _load_smolvlm(self, model_id: str, device: str):
        """Load a lightweight VLM fallback that fits better on 8GB RAM."""
        import torch
        from transformers import AutoProcessor
        from app.vlm_config import VLM_CACHE_DIR

        try:
            from transformers import AutoModelForImageTextToText
            model_cls = AutoModelForImageTextToText
        except ImportError:
            from transformers import AutoModelForVision2Seq
            model_cls = AutoModelForVision2Seq

        logger.info("Loading SmolVLM-256M-Instruct on %s...", device)

        if device == "cpu":
            self._configure_torch_cpu_runtime()

        load_kwargs = {
            "cache_dir": str(VLM_CACHE_DIR),
            "trust_remote_code": True,
            "low_cpu_mem_usage": True,
            "_attn_implementation": "eager",
        }

        if device == "cuda":
            load_kwargs["dtype"] = torch.float16
            load_kwargs["device_map"] = {"": "cuda"}
        else:
            load_kwargs["dtype"] = torch.bfloat16
            load_kwargs["device_map"] = {"": "cpu"}

        self.model = model_cls.from_pretrained(model_id, **load_kwargs)
        self.model.eval()

        self.processor = AutoProcessor.from_pretrained(
            model_id,
            cache_dir=str(VLM_CACHE_DIR),
            trust_remote_code=True,
        )

        try:
            image_processor = getattr(self.processor, "image_processor", None)
            if image_processor is not None and hasattr(image_processor, "size"):
                image_processor.size = {"longest_edge": 384}
        except Exception:
            pass

        self.model_name = "smolvlm-256m"
        self.device = device
        logger.info("SmolVLM-256M-Instruct loaded successfully")

    def _infer_qwen(self, images: list[Image.Image], prompt: str) -> str:
        """Run inference with Qwen2.5-VL."""
        from qwen_vl_utils import process_vision_info

        # Build messages with images
        content = []
        for img in images:
            content.append({"type": "image", "image": img})
        content.append({"type": "text", "text": prompt})

        messages = [{"role": "user", "content": content}]

        text_input = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)

        inputs = self.processor(
            text=[text_input],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(self.model.device)

        from app.vlm_config import VLM_MAX_NEW_TOKENS, VLM_TEMPERATURE

        import torch
        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=VLM_MAX_NEW_TOKENS,
                temperature=VLM_TEMPERATURE,
                do_sample=VLM_TEMPERATURE > 0,
            )

        # Decode only the generated tokens
        generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
        return self.processor.decode(generated_ids, skip_special_tokens=True)

    def _infer_moondream(self, images: list[Image.Image], prompt: str) -> str:
        """Run inference with moondream2. Handles API variations across versions."""
        from app.vlm_config import VLM_MAX_NEW_TOKENS

        # moondream2 handles single image — create composite for multi-image
        if len(images) > 1:
            composite = self._create_composite_image(images)
        else:
            composite = images[0]

        try:
            if hasattr(self.model, "encode_image") and hasattr(self.model, "answer_question"):
                enc_image = self.model.encode_image(composite)
                try:
                    answer = self.model.answer_question(enc_image, prompt, self.tokenizer)
                except TypeError:
                    answer = self.model.answer_question(enc_image, prompt)
                return _normalize_moondream_output(answer)
        except Exception as e:
            logger.info("moondream2 answer_question path unavailable (%s), trying query()", e)

        try:
            if hasattr(self.model, "query"):
                answer = self.model.query(composite, prompt)
                return _normalize_moondream_output(answer)
        except Exception as e:
            logger.info("moondream2 query path unavailable (%s), trying generate()", e)

        try:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            if hasattr(inputs, "to"):
                inputs = inputs.to(self.model.device)
            import torch
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=VLM_MAX_NEW_TOKENS,
                )
            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception as e:
            logger.error(f"moondream2 fallback generate also failed: {e}")
            return '{"reasoning": "moondream2 inference failed", "overall_score": 0.5}'

    def _infer_smolvlm(self, images: list[Image.Image], prompt: str) -> str:
        """Run inference with SmolVLM."""
        from app.vlm_config import VLM_MAX_NEW_TOKENS

        messages = [{
            "role": "user",
            "content": ([{"type": "image"} for _ in images] + [{"type": "text", "text": prompt}]),
        }]

        prompt_text = self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
        )

        inputs = self.processor(
            text=prompt_text,
            images=images,
            return_tensors="pt",
        )
        if hasattr(inputs, "to"):
            inputs = inputs.to(self.device)

        import torch

        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=VLM_MAX_NEW_TOKENS,
                do_sample=False,
            )

        decoded = self.processor.batch_decode(output_ids, skip_special_tokens=True)[0]
        if "Assistant:" in decoded:
            decoded = decoded.split("Assistant:")[-1].strip()
        return decoded

    def _create_composite_image(self, images: list[Image.Image]) -> Image.Image:
        """
        Create a side-by-side composite image with labels.
        Left side: registration frames, Right side: auth frames.
        """
        # Split into registration (first half) and auth (second half) frames
        n = len(images)
        mid = n // 2 if n > 1 else 1

        # Resize all to same height
        target_h = 320
        resized = []
        for img in images:
            w, h = img.size
            scale = target_h / h
            resized.append(img.resize((int(w * scale), target_h), Image.LANCZOS))

        # Total width
        total_w = sum(img.size[0] for img in resized) + (n - 1) * 10  # 10px gaps
        label_h = 30

        # Create composite
        composite = Image.new("RGB", (total_w, target_h + label_h), (40, 40, 40))

        x = 0
        for i, img in enumerate(resized):
            composite.paste(img, (x, label_h))
            x += img.size[0] + 10

        return composite

    def judge_authentication(
        self,
        registration_frames: list[np.ndarray],
        authentication_frames: list[np.ndarray],
    ) -> VLMJudgment:
        """
        Run VLM reasoning on registration vs authentication frames.

        This is the main entry point for the VLM Judge layer.

        Args:
            registration_frames: 1-3 BGR reference frames from registration
            authentication_frames: 1-3 BGR frames from current auth attempt

        Returns:
            VLMJudgment with structured decision and reasoning
        """
        if not self.loaded:
            self._load_model()

        if not self.loaded:
            return _neutral_judgment(self.load_error or "VLM model not loaded")

        if not registration_frames or not authentication_frames:
            return _neutral_judgment("Missing frames for VLM comparison")

        t_start = time.perf_counter()

        try:
            with self._infer_lock:
                from app.vlm_config import (
                    VLM_AUTH_FRAME_COUNT,
                    VLM_JUDGE_PROMPT,
                    VLM_JUDGE_PROMPT_SIMPLE,
                    VLM_JUDGE_PROMPT_SMALL_MODEL,
                    VLM_MOONDREAM_AUTH_FRAME_COUNT,
                    VLM_MOONDREAM_REF_FRAME_COUNT,
                    VLM_REF_FRAME_COUNT,
                    VLM_SMALL_MODEL_AUTH_FRAME_COUNT,
                    VLM_SMALL_MODEL_REF_FRAME_COUNT,
                )

                if self.model_name == "qwen2.5-vl-3b":
                    reg_frame_limit = VLM_REF_FRAME_COUNT
                    auth_frame_limit = VLM_AUTH_FRAME_COUNT
                    prompt = VLM_JUDGE_PROMPT
                elif self.model_name == "smolvlm-256m":
                    reg_frame_limit = VLM_SMALL_MODEL_REF_FRAME_COUNT
                    auth_frame_limit = VLM_SMALL_MODEL_AUTH_FRAME_COUNT
                    prompt = VLM_JUDGE_PROMPT_SMALL_MODEL
                else:
                    reg_frame_limit = VLM_MOONDREAM_REF_FRAME_COUNT
                    auth_frame_limit = VLM_MOONDREAM_AUTH_FRAME_COUNT
                    prompt = VLM_JUDGE_PROMPT_SIMPLE

                # Convert frames to PIL images
                reg_subset = self._select_frame_subset(registration_frames, reg_frame_limit)
                auth_subset = self._select_frame_subset(authentication_frames, auth_frame_limit)
                reg_pils = [_bgr_to_pil(f) for f in reg_subset]
                auth_pils = [_bgr_to_pil(f) for f in auth_subset]

                # Combine: registration frames first, then auth frames
                all_images = reg_pils + auth_pils

                # Add frame context to prompt
                n_reg = len(reg_pils)
                n_auth = len(auth_pils)
                frame_context = (
                    f"\n\nNote: You are seeing {n_reg + n_auth} images total. "
                    f"The first {n_reg} image(s) are REGISTRATION reference frames. "
                    f"The last {n_auth} image(s) are AUTHENTICATION attempt frames. "
                    "Use the registration frames for stable identity cues. "
                    "Use the authentication frames for device detection, screen detection, "
                    "hand-held media detection, full-face visibility, eye blink, and motion."
                )
                prompt += frame_context

                # Run inference
                if self.model_name == "qwen2.5-vl-3b":
                    raw_output = self._infer_qwen(all_images, prompt)
                elif self.model_name == "moondream2":
                    raw_output = self._infer_moondream(all_images, prompt)
                elif self.model_name == "smolvlm-256m":
                    raw_output = self._infer_smolvlm(all_images, prompt)
                else:
                    return _neutral_judgment(f"Unknown model: {self.model_name}")

                logger.info(f"VLM raw output ({self.model_name}): {raw_output[:300]}...")

                # Parse structured JSON from VLM output
                parsed = _parse_vlm_json(raw_output)
                parsed = _normalize_parsed_vlm_output(parsed, raw_output)

                inference_ms = (time.perf_counter() - t_start) * 1000

                judgment = VLMJudgment(
                    same_person=bool(parsed.get("same_person", True)),
                    same_person_confidence=float(parsed.get("same_person_confidence", 0.5)),
                    is_live=bool(parsed.get("is_live", True)),
                    liveness_confidence=float(parsed.get("liveness_confidence", 0.5)),
                    is_authentic=bool(parsed.get("is_authentic", True)),
                    authenticity_confidence=float(parsed.get("authenticity_confidence", 0.5)),
                    overall_score=float(parsed.get("overall_score", 0.5)),
                    reasoning=str(parsed.get("reasoning", raw_output[:500])),
                    red_flags=list(parsed.get("red_flags", [])),
                    model_used=self.model_name,
                    inference_time_ms=round(inference_ms, 1),
                )

                logger.info(
                    f"VLM judgment: same_person={judgment.same_person} "
                    f"({judgment.same_person_confidence:.2f}), "
                    f"live={judgment.is_live} ({judgment.liveness_confidence:.2f}), "
                    f"authentic={judgment.is_authentic} ({judgment.authenticity_confidence:.2f}), "
                    f"overall={judgment.overall_score:.2f}, "
                    f"model={judgment.model_used}, "
                    f"time={judgment.inference_time_ms:.0f}ms"
                )

                return judgment

        except Exception as e:
            inference_ms = (time.perf_counter() - t_start) * 1000
            logger.error(f"VLM inference error: {e}", exc_info=True)
            result = _neutral_judgment(f"VLM inference error: {str(e)[:200]}")
            result.inference_time_ms = round(inference_ms, 1)
            return result

    @staticmethod
    def _select_frame_subset(frames: list[np.ndarray], limit: int) -> list[np.ndarray]:
        """Select an evenly spaced subset of frames for VLM inference."""
        if limit <= 1:
            return [frames[len(frames) // 2]]

        if len(frames) <= limit:
            return list(frames)

        indices = np.linspace(0, len(frames) - 1, limit, dtype=int)
        unique_indices = np.unique(indices)
        return [frames[int(idx)] for idx in unique_indices]

    def get_status(self) -> dict:
        """Return VLM model status for the /vlm/status endpoint."""
        return {
            "loaded": self.loaded,
            "model_name": self.model_name,
            "model_id": self.model_id,
            "device": self.device,
            "load_attempted": self._load_attempted,
            "error": self.load_error,
        }
