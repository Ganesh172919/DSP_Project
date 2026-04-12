"""
video_utils.py - Shared helpers for decoding browser-recorded video uploads.

OpenCV remains the first decode path to preserve the current behaviour.
If OpenCV cannot decode the uploaded video (common for WebM on Windows),
the helpers fall back to an FFmpeg binary exposed by imageio-ffmpeg.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_KNOWN_VIDEO_SUFFIXES = {
    ".avi",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".ogg",
    ".ogv",
    ".webm",
}


def infer_video_suffix(
    filename: str | None = None,
    content_type: str | None = None,
    default: str = ".webm",
) -> str:
    """Infer the best temp-file suffix for an uploaded video."""
    if filename:
        suffix = Path(filename).suffix.lower()
        if suffix in _KNOWN_VIDEO_SUFFIXES:
            return suffix

    if content_type:
        content_type = content_type.lower()
        if "mp4" in content_type:
            return ".mp4"
        if "quicktime" in content_type or "mov" in content_type:
            return ".mov"
        if "webm" in content_type:
            return ".webm"
        if "ogg" in content_type:
            return ".ogv"

    return default


def sample_evenly_spaced_frames(
    frames: list[np.ndarray],
    count: int,
) -> list[np.ndarray]:
    """Sample evenly spaced frames from an in-memory frame list."""
    if not frames or count <= 0:
        return []

    if len(frames) <= count:
        return [frame.copy() for frame in frames]

    indices = np.linspace(0, len(frames) - 1, count, dtype=int)
    unique_indices = np.unique(indices)
    return [frames[int(idx)].copy() for idx in unique_indices]


def decode_video_bytes(
    video_bytes: bytes,
    suffix: str = ".webm",
) -> list[np.ndarray]:
    """
    Decode raw video bytes into a list of BGR frames.

    Decode order:
      1. OpenCV VideoCapture
      2. FFmpeg via imageio-ffmpeg
    """
    if not video_bytes:
        return []

    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)

    try:
        with open(temp_path, "wb") as handle:
            handle.write(video_bytes)

        frames = _decode_with_opencv(temp_path)
        if frames:
            return frames

        logger.info(
            "OpenCV could not decode %s, trying FFmpeg fallback for %s",
            suffix,
            temp_path,
        )
        return _decode_with_ffmpeg(temp_path)
    finally:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass


def extract_evenly_spaced_frames(
    video_bytes: bytes,
    count: int,
    suffix: str = ".webm",
) -> list[np.ndarray]:
    """Decode a video and return evenly spaced frames."""
    frames = decode_video_bytes(video_bytes, suffix=suffix)
    return sample_evenly_spaced_frames(frames, count)


def _decode_with_opencv(video_path: str) -> list[np.ndarray]:
    """Decode a video file using OpenCV."""
    frames: list[np.ndarray] = []
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        return frames

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
    finally:
        cap.release()

    return frames


def _decode_with_ffmpeg(video_path: str) -> list[np.ndarray]:
    """Decode a video file with imageio-ffmpeg's bundled FFmpeg binary."""
    try:
        import imageio_ffmpeg
    except ImportError:
        logger.warning(
            "imageio-ffmpeg is not installed, FFmpeg video fallback is unavailable"
        )
        return []

    frames: list[np.ndarray] = []

    try:
        reader = imageio_ffmpeg.read_frames(
            video_path,
            pix_fmt="rgb24",
            output_params=["-loglevel", "error"],
        )
        meta = next(reader)
        size = meta.get("size")
        if not size or len(size) != 2:
            logger.warning("FFmpeg reader did not expose frame size metadata")
            return []

        width, height = int(size[0]), int(size[1])
        expected_size = width * height * 3

        for frame_bytes in reader:
            if not frame_bytes:
                continue

            frame = np.frombuffer(frame_bytes, dtype=np.uint8)
            if frame.size != expected_size:
                logger.warning(
                    "Skipping FFmpeg frame with unexpected size %s (expected %s)",
                    frame.size,
                    expected_size,
                )
                continue

            frame = frame.reshape((height, width, 3))
            frames.append(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    except Exception as exc:
        logger.warning("FFmpeg fallback decode failed: %s", exc)
        return []

    return frames
