from __future__ import annotations

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="DeepShield Guardian Face Analysis Service")

KEY_INDICES = [10, 33, 61, 70, 105, 127, 133, 145, 152, 159, 195, 205, 234, 263, 291, 300, 334, 356, 362, 374, 386, 454, 468, 473]


class ExtractionRequest(BaseModel):
    landmarks: list[list[float]] = Field(default_factory=list)


def _array(landmarks: list[list[float]]) -> np.ndarray:
    if not landmarks:
        return np.zeros((0, 3), dtype=np.float32)
    points = np.array(landmarks, dtype=np.float32)
    if points.shape[1] == 2:
        points = np.column_stack([points, np.zeros((points.shape[0],), dtype=np.float32)])
    return points


def compute_embedding(landmarks: list[list[float]]) -> list[float]:
    points = _array(landmarks)
    if points.size == 0:
        return [0.0] * 128
    subset = points[KEY_INDICES]
    center = subset.mean(axis=0, keepdims=True)
    scale = np.linalg.norm(subset[1] - subset[13]) or 1.0
    normalized = ((subset - center) / scale).reshape(-1)
    projection = np.random.default_rng(42).normal(0, 0.25, size=(normalized.shape[0], 128))
    embedding = normalized @ projection
    embedding = embedding / (np.linalg.norm(embedding) or 1.0)
    return embedding.astype(float).round(6).tolist()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/extract")
async def extract(request: ExtractionRequest) -> dict[str, list[float]]:
    return {"embedding": compute_embedding(request.landmarks)}

