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
            "hand_near_face": False,
            "quality_hint": "Ready",
        },
    )

    assert result["quality_score"] >= 70


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
