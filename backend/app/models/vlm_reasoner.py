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


def _bgr_to_pil(frame_bgr: np.ndarray, max_size: int = 512) -> Image.Image:
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
        match = re.search(rf'"{key}"\s*:\s*(true|false)', text, re.IGNORECASE)
        if match:
            result[key] = match.group(1).lower() == "true"

    # Try to extract float values
    for key in ["same_person_confidence", "liveness_confidence",
                 "authenticity_confidence", "overall_score"]:
        match = re.search(rf'"{key}"\s*:\s*([\d.]+)', text)
        if match:
            result[key] = float(match.group(1))

    return result


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

    def _load_model(self):
        """Lazy-load the VLM model based on available hardware."""
        if self._load_attempted:
            return

        self._load_attempted = True

        from app.vlm_config import select_vlm_model, VLM_CACHE_DIR

        model_id, quantize, device = select_vlm_model()

        if model_id is None:
            logger.warning("VLM: No suitable model found — VLM reasoning disabled")
            return

        self.model_id = model_id
        self.device = device

        try:
            if "qwen" in model_id.lower():
                self._load_qwen(model_id, quantize, device)
            elif "moondream" in model_id.lower():
                self._load_moondream(model_id, device)
            else:
                logger.error(f"VLM: Unknown model ID: {model_id}")
                return

            self.loaded = True
            logger.info(f"VLM loaded: {self.model_name} on {self.device}")

        except Exception as e:
            logger.error(f"VLM load failed ({model_id}): {e}", exc_info=True)

            # Try fallback to moondream if Qwen failed
            if "qwen" in model_id.lower():
                logger.info("VLM: Falling back to moondream2...")
                try:
                    from app.vlm_config import MOONDREAM_MODEL_ID
                    fb_device = "cuda" if device == "cuda" else "cpu"
                    self._load_moondream(MOONDREAM_MODEL_ID, fb_device)
                    self.loaded = True
                    logger.info(f"VLM fallback loaded: {self.model_name} on {self.device}")
                except Exception as e2:
                    logger.error(f"VLM fallback also failed: {e2}", exc_info=True)

    def _load_qwen(self, model_id: str, quantize: str, device: str):
        """Load Qwen2.5-VL-3B-Instruct with 4-bit quantization."""
        import torch
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
        from app.vlm_config import VLM_CACHE_DIR

        logger.info(f"Loading Qwen2.5-VL ({quantize}) on {device}...")

        load_kwargs = {
            "cache_dir": str(VLM_CACHE_DIR),
            "trust_remote_code": True,
            "torch_dtype": torch.float16,
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
        """Load moondream2 model."""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from app.vlm_config import VLM_CACHE_DIR

        logger.info(f"Loading moondream2 on {device}...")

        dtype = torch.float16 if device == "cuda" else torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            cache_dir=str(VLM_CACHE_DIR),
            trust_remote_code=True,
            torch_dtype=dtype,
            device_map={"": device} if device == "cuda" else None,
        )

        if device == "cpu":
            self.model = self.model.to("cpu")

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            cache_dir=str(VLM_CACHE_DIR),
            trust_remote_code=True,
        )
        self.model_name = "moondream2"
        self.device = device

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
        """Run inference with moondream2."""
        from app.vlm_config import VLM_MAX_NEW_TOKENS

        # moondream2 handles single image typically.
        # For multi-image, we create a composite image.
        if len(images) > 1:
            composite = self._create_composite_image(images)
        else:
            composite = images[0]

        # moondream2's API: model.answer_question(enc_image, question, tokenizer)
        enc_image = self.model.encode_image(composite)
        answer = self.model.answer_question(
            enc_image, prompt, self.tokenizer,
        )

        return answer

    def _create_composite_image(self, images: list[Image.Image]) -> Image.Image:
        """
        Create a side-by-side composite image with labels.
        Left side: registration frames, Right side: auth frames.
        """
        # Split into registration (first half) and auth (second half) frames
        n = len(images)
        mid = n // 2 if n > 1 else 1

        # Resize all to same height
        target_h = 384
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
            return _neutral_judgment("VLM model not loaded")

        if not registration_frames or not authentication_frames:
            return _neutral_judgment("Missing frames for VLM comparison")

        t_start = time.perf_counter()

        try:
            # Convert frames to PIL images
            reg_pils = [_bgr_to_pil(f) for f in registration_frames[:3]]
            auth_pils = [_bgr_to_pil(f) for f in authentication_frames[:3]]

            # Combine: registration frames first, then auth frames
            all_images = reg_pils + auth_pils

            # Select prompt based on model
            from app.vlm_config import VLM_JUDGE_PROMPT, VLM_JUDGE_PROMPT_SIMPLE

            if self.model_name == "qwen2.5-vl-3b":
                prompt = VLM_JUDGE_PROMPT
            else:
                # moondream2 works better with simpler prompts
                prompt = VLM_JUDGE_PROMPT_SIMPLE

            # Add frame context to prompt
            n_reg = len(reg_pils)
            n_auth = len(auth_pils)
            frame_context = (
                f"\n\nNote: You are seeing {n_reg + n_auth} images total. "
                f"The first {n_reg} image(s) are REGISTRATION reference frames. "
                f"The last {n_auth} image(s) are AUTHENTICATION attempt frames."
            )
            prompt += frame_context

            # Run inference
            if self.model_name == "qwen2.5-vl-3b":
                raw_output = self._infer_qwen(all_images, prompt)
            elif self.model_name == "moondream2":
                raw_output = self._infer_moondream(all_images, prompt)
            else:
                return _neutral_judgment(f"Unknown model: {self.model_name}")

            logger.info(f"VLM raw output ({self.model_name}): {raw_output[:300]}...")

            # Parse structured JSON from VLM output
            parsed = _parse_vlm_json(raw_output)

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

    def get_status(self) -> dict:
        """Return VLM model status for the /vlm/status endpoint."""
        return {
            "loaded": self.loaded,
            "model_name": self.model_name,
            "model_id": self.model_id,
            "device": self.device,
            "load_attempted": self._load_attempted,
        }
