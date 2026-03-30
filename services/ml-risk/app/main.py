from __future__ import annotations

import base64
import io

import numpy as np
from fastapi import FastAPI
from PIL import Image
from pydantic import BaseModel, Field

app = FastAPI(title="DeepShield Guardian Risk Service")


class RiskRequest(BaseModel):
    frame_b64: str | None = None
    client_metrics: dict = Field(default_factory=dict)


def _decode(frame_b64: str | None) -> np.ndarray | None:
    if not frame_b64:
        return None
    if "," in frame_b64:
        frame_b64 = frame_b64.split(",", 1)[1]
    payload = base64.b64decode(frame_b64)
    image = Image.open(io.BytesIO(payload)).convert("RGB")
    return np.asarray(image, dtype=np.float32)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(request: RiskRequest) -> dict:
    image = _decode(request.frame_b64)
    if image is None:
        return {
            "pad_score": 0.65,
            "deepfake_score": 0.65,
            "quality_score": 55.0,
            "guidance": ["Frame unavailable"],
            "anomalies": [],
        }

    gray = image.mean(axis=2)
    gx = np.abs(np.diff(gray, axis=1)).mean()
    gy = np.abs(np.diff(gray, axis=0)).mean()
    sharpness = max(0.0, min(float((gx + gy) / 50), 1.0))
    exposure = float(gray.mean() / 255.0)
    frequency = np.abs(np.fft.fftshift(np.fft.fft2(gray)))
    frequency = frequency / (np.max(frequency) or 1.0)
    high_energy = float(frequency[frequency > np.percentile(frequency, 90)].mean())
    pad_score = max(0.0, min(0.4 * sharpness + 0.3 * (1 - abs(exposure - 0.5)) + 0.3 * min(high_energy * 6, 1.0), 1.0))
    deepfake_score = max(0.0, min(0.5 * min(high_energy * 6, 1.0) + 0.5 * sharpness, 1.0))
    return {
        "pad_score": round(pad_score, 4),
        "deepfake_score": round(deepfake_score, 4),
        "quality_score": round((0.5 * sharpness + 0.5 * (1 - abs(exposure - 0.5))) * 100, 2),
        "guidance": ["Capture quality is acceptable."],
        "anomalies": [],
    }
