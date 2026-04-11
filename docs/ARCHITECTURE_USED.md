# Architecture Used

## Architecture Style

The project uses a layered full-stack architecture:

- Presentation layer: React frontend.
- API layer: FastAPI routes.
- Pipeline layer: centralized authentication decision engine.
- AI model layer: independent face, liveness, deepfake, and challenge modules.
- Security layer: encryption, JWT, rate limiting, and CORS.
- Data layer: SQLite through SQLAlchemy.

This separation keeps user interaction, HTTP handling, AI inference, security operations, and persistence understandable and independently maintainable.

## High-Level Architecture

```text
User browser
  |
  | camera frames / video
  v
React + Vite frontend
  |
  | multipart/form-data
  v
FastAPI backend
  |
  | route handlers
  v
AuthPipeline
  |-- AntiInjectionGuard
  |-- FaceDetector
  |-- FaceRecognizer
  |-- LivenessDetector
  |-- DeepfakeDetector
  `-- InstructionVerifier
  |
  | encrypted embeddings, logs, challenges
  v
SQLite database
```

## Frontend Layer

The frontend is implemented with React 18, Vite, Axios, and React Router.

Main files:

- `src/App.jsx`: routing and navigation.
- `src/pages/Register.jsx`: user registration and five-frame capture.
- `src/pages/Login.jsx`: username entry, 4-second video recording, and result display.
- `src/components/CameraCapture.jsx`: reusable still-frame capture component.
- `src/components/VideoRecorder.jsx`: reusable video recorder component.
- `src/components/InstructionChallenge.jsx`: challenge video capture component.
- `src/api/client.js`: Axios client configured with `/api/v1` base URL.

## Backend Layer

The backend is implemented with FastAPI.

Main responsibilities:

- Decode uploaded images and videos.
- Validate users and duplicate registration attempts.
- Run the authentication pipeline.
- Encrypt and decrypt embeddings.
- Create JWTs after successful authentication.
- Log attempts in SQLite.
- Apply CORS and rate limiting.

Main files:

- `app/main.py`: API entry point.
- `app/pipeline.py`: orchestration and decision logic.
- `app/config.py`: thresholds, paths, model configuration, and security settings.
- `app/crypto.py`: AES and JWT helpers.
- `app/db/models.py`: database schema.
- `app/db/crud.py`: database access helpers.

## AI Pipeline Layer

### Layer 0: Anti-Injection Guard

Checks whether a camera source appears physical or virtual. It can inspect camera names, PRNU-like noise variance, and frame metadata. Current upload routes skip this layer because uploaded files do not provide live camera device metadata.

### Layer 1: Face Detection And Alignment

Uses OpenCV YuNet to detect the face and five landmarks. The module rejects low-quality detections and aligns the face to `112 x 112` for ArcFace.

### Layer 2: Face Recognition

Uses ArcFace `w600k_r50.onnx` with ONNX Runtime to generate 512-dimensional normalized embeddings. Authentication compares a new embedding with the decrypted stored template using cosine similarity.

### Layer 3: Liveness Detection

Combines MobileNetV3-Small features, texture analysis, color analysis, moire detection, boundary analysis, optical flow, micro-movement, rPPG, and optional instruction score.

### Layer 4: Deepfake Detection

Combines FFT spectral analysis, EfficientNet-B0 feature analysis, boundary artifacts, eye reflection checks, skin uniformity, color correlation, and temporal flicker.

### Layer 5: Instruction Verification

Uses MediaPipe FaceMesh and Hands for optional active challenge verification. The challenge endpoints ask for two instruction videos and verify them against the issued challenge.

## Data Layer

SQLite stores:

- `users`: username, email, encrypted embedding, face quality, creation time.
- `auth_logs`: liveness score, deepfake score, similarity score, injection confidence, flags, decision, denial reason.
- `challenge_logs`: challenge ID, instruction IDs, instruction results, completion metadata.

## Security Layer

Implemented security features:

- AES-256-GCM encryption for face embeddings.
- RS256 JWT generation after successful authentication.
- Rate limiting with SlowAPI.
- CORS restriction for local frontend development origins.
- Audit logging of authentication attempts.

Production hardening still requires secure secret handling, key rotation, HTTPS, stricter CORS, and migration-managed database deployment.

## Why This Architecture Was Chosen

- Modular AI components make the methodology easier to explain and test.
- FastAPI provides a simple typed API layer for multipart uploads.
- React provides a practical browser camera workflow.
- SQLite is enough for a local academic prototype.
- ONNX Runtime allows ArcFace inference without the heavier InsightFace runtime dependency.
- Layered decisions make the system more resistant to single-point model failure.

## Latest Architecture Expansion: VLM Layer

The newest architecture adds a VLM hybrid layer as an additive branch:

```text
React VLM pages
  -> /api/v1/vlm routes
  -> VLMAuthPipeline
       |-- existing AuthPipeline
       |-- VLMReasoner
       |-- VLM reference-frame loader
       `-- fusion and veto logic
  -> users + auth_logs + vlm_registrations
  -> data/vlm_ref_frames/{user_id}
```

The VLM layer does not alter the original `AuthPipeline` decision sequence. It runs after the traditional video path grants access. If the traditional path denies access, VLM inference is skipped to save compute and preserve the original denial reason.

Additional files introduced by this architecture:

- `backend/app/vlm_routes.py`
- `backend/app/vlm_pipeline.py`
- `backend/app/vlm_config.py`
- `backend/app/models/vlm_reasoner.py`
- `backend/app/db/vlm_models.py`
- `backend/app/db/vlm_crud.py`
- `frontend/src/pages/VLMRegister.jsx`
- `frontend/src/pages/VLMLogin.jsx`

Additional documentation is available in `docs/VLM_HYBRID_AUTHENTICATION.md`.
