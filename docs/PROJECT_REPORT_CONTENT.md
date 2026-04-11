# Project Report Content

## Title

AI-Based Facial Authentication System with Liveness Detection and Deepfake Protection

## Abstract

Facial authentication is convenient but vulnerable to attacks such as printed photos, screen replays, recorded videos, and AI-generated faces. This project implements a full-stack facial authentication system that combines face recognition with liveness detection, anti-spoofing, and deepfake screening. The frontend captures registration images and authentication videos through the browser, while the FastAPI backend runs a layered AI pipeline using YuNet face detection, ArcFace embeddings, liveness scoring, deepfake risk estimation, and optional instruction challenge verification. Biometric templates are encrypted with AES-256-GCM before being stored in SQLite, and successful authentication returns an RS256 JWT.

## Introduction

Face recognition alone is not sufficient for secure authentication because it only answers whether two face images are visually similar. It does not prove that the face is live, captured from a real person, or free from synthetic manipulation. This project addresses that limitation by combining identity verification with multiple independent security checks.

## Problem Statement

The goal is to build a secure and explainable facial authentication system that can:

- Register a user's face securely.
- Authenticate the same user from camera input.
- Reject spoofed, replayed, or manipulated inputs.
- Provide clear scores and denial reasons.
- Store biometric data safely.

## Objectives

- Implement browser-based face registration and login.
- Use YuNet for face detection and alignment.
- Use ArcFace for 512-dimensional face embeddings.
- Encrypt stored biometric templates.
- Add liveness detection for photo and replay resistance.
- Add deepfake detection for synthetic face resistance.
- Add optional active instruction challenges.
- Log authentication attempts for auditability.
- Provide clear developer and reviewer documentation.

## System Methodology

### Registration Methodology

The user provides a username and email, then captures five face frames through the browser. The backend detects and aligns faces in each frame, performs a quick liveness check, extracts ArcFace embeddings, averages the accepted embeddings, normalizes the result, encrypts it, and stores it as the user's face template.

### Authentication Methodology

The user records a short video. The backend extracts frames, uses the middle frame for face recognition, and uses the full frame sequence for liveness and deepfake checks. The final decision is based on thresholds for face confidence, liveness, deepfake probability, and face similarity.

### Face Detection

OpenCV YuNet is used because it is lightweight, returns five facial landmarks, and integrates cleanly with OpenCV. The five landmarks are used to align the face to the ArcFace input geometry.

### Face Recognition

ArcFace `w600k_r50.onnx` generates normalized 512-dimensional embeddings. During authentication, cosine similarity is computed against the encrypted stored template after decryption.

### Liveness Detection

The liveness layer uses:

- MobileNetV3-Small image features.
- Texture analysis.
- Color distribution checks.
- Moire pattern detection.
- Face boundary checks.
- Optical flow when video is available.
- Micro-movement when FaceMesh landmarks are available.
- rPPG pulse estimation when enough frames exist.
- Optional instruction challenge score.

### Deepfake Detection

The deepfake layer uses:

- FFT spectral analysis.
- EfficientNet-B0 feature analysis.
- Boundary artifact detection.
- Eye reflection consistency.
- Skin uniformity analysis.
- RGB channel correlation.
- Temporal flicker in video.

### Decision Engine

The system denies access when:

- No valid face is detected.
- Liveness score is below `0.70`.
- Deepfake probability is above `0.30`.
- Required challenge instruction fails.
- ArcFace similarity is below `0.40`.

Otherwise, the system grants access and returns a JWT.

## System Implementation

The backend is built with FastAPI and SQLAlchemy. It exposes endpoints for registration, video authentication, challenge authentication, instruction listing, user history, and health checks. The frontend is built with React and Vite and uses browser media APIs for camera capture.

## Tools And Technologies

| Category | Tools |
| --- | --- |
| Frontend | React, Vite, Axios, React Router |
| Backend | FastAPI, Uvicorn |
| AI/CV | OpenCV, ONNX Runtime, PyTorch, Torchvision, MediaPipe |
| Data | SQLite, SQLAlchemy |
| Security | AES-256-GCM, RS256 JWT, SlowAPI |
| Training | scikit-learn metrics, PyTorch training scripts |

## Architecture

```text
React frontend
  -> FastAPI backend
  -> AuthPipeline
  -> AI modules
  -> Decision engine
  -> SQLite and JWT response
```

## Results And Discussion

The system returns detailed per-attempt results:

- Authentication decision.
- Overall confidence.
- Liveness score.
- Deepfake probability.
- ArcFace similarity score.
- Injection confidence.
- Threat flags.
- Processing time.

No dataset-backed benchmark values are committed. The repository includes an evaluation script capable of producing FAR, FRR, EER, AUC, precision, recall, F1, and latency when a suitable dataset is provided.

## Strengths

- Multi-layer security pipeline.
- Encrypted biometric storage.
- Explainable decisions with score breakdown.
- Modular architecture.
- Video-based login for temporal analysis.
- Optional active challenges for stronger replay resistance.
- Extendable training and evaluation scripts.

## Limitations

- Thresholds need calibration on representative datasets.
- Upload routes cannot fully validate physical camera hardware.
- Some anti-spoof and deepfake checks are heuristic when fine-tuned weights are absent.
- Production deployment requires stronger secret management.
- Runtime and training deepfake model variants should be aligned.

## Future Scope

- Add benchmark datasets and publish evaluation tables.
- Add automated tests for APIs and decision thresholds.
- Integrate fine-tuned liveness and deepfake models.
- Improve live-camera anti-injection integration.
- Add Docker Compose and deployment documentation.
- Add database migrations.
- Add model cards, fairness evaluation, and privacy documentation.

## Conclusion

The project successfully demonstrates an AI-based facial authentication system that combines face matching with liveness and deepfake protection. Its layered architecture provides stronger security and clearer explanations than basic face recognition alone, while leaving a practical path for future model calibration and production hardening.

## Addendum For Latest VLM Version

The latest version extends the project with a VLM hybrid authentication path. In addition to the original frame-based registration and video login flow, the system now includes VLM registration and VLM login pages. VLM registration records a short video, builds the normal encrypted ArcFace template, and stores selected reference frames for later comparison. VLM authentication first runs the existing traditional pipeline and then, only after a traditional grant, uses a Vision Language Model to compare registration frames with current authentication frames.

This addition improves explainability because the VLM returns natural-language reasoning along with identity, liveness, authenticity, and overall scores. The final VLM confidence is fused with the traditional confidence using a weighted rule. The VLM can also veto a traditional grant when it reports high-confidence concerns.

For a report section, this can be described as an optional semantic reasoning layer added on top of the existing numeric biometric pipeline. The original system remains available and serves as the fallback path when VLM dependencies or hardware are unavailable.
