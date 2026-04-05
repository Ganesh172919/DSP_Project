import base64
import io

import numpy as np
from PIL import Image

from app.services.risk import analyze_frame_risk


def _encode_png(array: np.ndarray) -> str:
    image = Image.fromarray(array.astype("uint8"), mode="RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")


def test_quality_score_rewards_clear_well_framed_capture():
    checker = np.indices((96, 96)).sum(axis=0) % 2
    checker = np.repeat(checker[:, :, None] * 255, 3, axis=2)
    frame_b64 = _encode_png(checker)

    result = analyze_frame_risk(
        frame_b64=frame_b64,
        client_metrics={
            "face_present": True,
            "face_size_ratio": 0.10,
            "pitch": 2.0,
            "roll": 1.0,
            "face_center_x": 0.5,
            "face_center_y": 0.48,
            "eye_line_y": 0.31,
            "face_top_margin": 0.14,
            "face_bottom_margin": 0.16,
            "hand_near_face": False,
            "quality_hint": "Ready",
        },
    )

    assert result["quality_score"] >= 70
    assert result["guidance"] == ["Capture quality is acceptable"]


def test_quality_score_stays_lower_for_unavailable_frame_without_face():
    result = analyze_frame_risk(
        frame_b64=None,
        client_metrics={
            "face_present": False,
            "face_size_ratio": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
            "hand_near_face": False,
            "quality_hint": "No face",
        },
    )

    assert result["quality_score"] < 50
    assert "Frame unavailable" in result["guidance"]


def test_quality_guidance_flags_low_camera_angle():
    checker = np.indices((96, 96)).sum(axis=0) % 2
    checker = np.repeat(checker[:, :, None] * 255, 3, axis=2)
    frame_b64 = _encode_png(checker)

    result = analyze_frame_risk(
        frame_b64=frame_b64,
        client_metrics={
            "face_present": True,
            "face_size_ratio": 0.11,
            "pitch": 2.0,
            "roll": 1.0,
            "face_center_x": 0.5,
            "face_center_y": 0.57,
            "eye_line_y": 0.45,
            "face_top_margin": 0.12,
            "face_bottom_margin": 0.04,
            "hand_near_face": False,
            "quality_hint": "Raise the camera to eye level",
        },
    )

    assert "Raise the camera to eye level" in result["guidance"]
    assert result["framing"] < 0.9
