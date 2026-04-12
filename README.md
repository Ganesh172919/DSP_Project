# DSP Project: AI-Based Facial Authentication with Liveness and Deepfake Protection

This repository implements a full-stack facial authentication system for secure user registration and login. It combines a React/Vite camera interface with a FastAPI backend and a layered AI pipeline that checks identity, face quality, liveness, replay/spoof indicators, and deepfake risk before returning an authentication decision.

The problem addressed is that ordinary face login can be attacked with printed photos, screen replays, virtual camera injection, recorded videos, and AI-generated or face-swapped images. This project improves the baseline by using multiple independent signals rather than relying only on face similarity.

## What Is Implemented

- Face registration from multiple webcam frames.
- Face authentication from a short webcam video.
- Optional still-image authentication endpoint for backward compatibility.
- Optional challenge-response authentication endpoints using face and hand instructions.
- Face detection and 5-point alignment with OpenCV YuNet.
- ArcFace embedding extraction with ONNX Runtime using `w600k_r50.onnx`.
- AES-256-GCM encryption of stored face embeddings.
- JWT token creation with RS256 after successful authentication.
- Liveness fusion using MobileNetV3-Small features, texture checks, color checks, moire analysis, optical flow, micro-movement, and rPPG when enough video frames are available.
- Deepfake risk estimation using FFT spectral analysis, EfficientNet-B0 feature analysis, boundary artifacts, eye reflection consistency, skin texture uniformity, color correlation, and temporal flicker.
- SQLite storage for users, encrypted embeddings, authentication logs, and challenge logs.
- Training scripts for optional fine-tuned liveness and deepfake models.

## Current Runtime Flow

The frontend currently exposes two main pages:

- `Register`: captures five still frames and sends them as multipart files to `/api/v1/register`.
- `Login`: records a 4-second WebM video and sends it to `/api/v1/authenticate/video`.

The backend also contains legacy and challenge endpoints:

- `/api/v1/authenticate` accepts a single uploaded image or video-like file.
- `/api/v1/challenge` issues two random instructions.
- `/api/v1/authenticate/challenge` verifies two instruction videos.
- `/api/v1/instructions` lists available instruction definitions for testing/debugging.

## Methodology

### 1. Input Capture

Registration uses five JPEG frames captured roughly one second apart. Authentication uses a short WebM video. Video authentication extracts frames with OpenCV and selects the middle frame for identity verification while using the full frame sequence for multi-frame liveness and deepfake checks.

### 2. Anti-Injection Guard

`AntiInjectionGuard` can validate a physical camera source through:

- Known virtual camera names such as OBS, ManyCam, Snap Camera, DroidCam, and related signatures.
- PRNU-style sensor noise variance checks.
- Frame metadata heuristics such as resolution, exact FPS, edge distribution, and rolling-shutter-like variation.

In the current HTTP upload routes, this check is skipped because the backend receives uploaded files rather than a live `cv2.VideoCapture` handle. The module is implemented and can be used when the backend owns the camera capture path.

### 3. Face Detection and Alignment

The detector uses OpenCV YuNet through `cv2.FaceDetectorYN` and the ONNX model `face_detection_yunet_2023mar.onnx`. YuNet returns:

- Bounding box.
- Five landmarks: eye centers, nose tip, and mouth corners.
- Confidence score.

The system rejects frames with low detection confidence, very small face area, excessive yaw, or excessive pitch. Accepted faces are aligned to a canonical `112 x 112` crop using a similarity transform matched to ArcFace reference landmarks.

### 4. Face Recognition

The recognizer uses ArcFace `w600k_r50.onnx`, loaded with ONNX Runtime. The aligned face is:

1. Converted from BGR to RGB.
2. Normalized to `[-1, 1]`.
3. Transposed to NCHW format.
4. Passed through ArcFace.
5. L2-normalized into a 512-dimensional embedding.

Registration averages embeddings from all accepted frames and L2-normalizes the final template. Authentication computes cosine similarity against the decrypted stored template. The current similarity threshold is `0.40`.

### 5. Liveness Detection

The liveness system fuses several signals:

- MobileNetV3-Small ImageNet features, or fine-tuned `liveness_mobilenetv3.pth` if present.
- Single-frame texture richness and color distribution analysis.
- FFT moire detection for screen replay artifacts.
- Face boundary checks.
- Optical flow and movement consistency when video frames are available.
- Micro-movement analysis when FaceMesh landmarks are available.
- rPPG green-channel forehead analysis when enough frames and landmarks are available.
- Optional instruction compliance score from challenge-based login.

The fused liveness score is compared against `FUSION_FINAL_THRESHOLD = 0.70`.

### 6. Deepfake Detection

Runtime deepfake detection uses a hybrid detector:

- FFT spectral decay and high-frequency anomaly checks.
- EfficientNet-B0 ImageNet feature analysis, or fine-tuned `deepfake_efficientnet.pth` if present.
- Boundary artifact checks for face blending.
- Eye reflection consistency checks.
- Skin texture uniformity checks.
- RGB channel correlation checks.
- Temporal flicker checks for video input.

The final deepfake probability is compared against `DEEPFAKE_FLAG_THRESHOLD = 0.30`. Scores above the threshold deny authentication with a synthetic-face flag.

Note: `backend/training/train_deepfake.py` can train a separate EfficientNet-B4 model and a spectral MLP. The current runtime detector in `backend/app/models/deepfake.py` uses EfficientNet-B0 unless that module is updated to load the B4 artifact.

### 7. Decision Engine

The backend grants access only when all required gates pass:

```text
Input frame/video
  -> optional anti-injection check
  -> YuNet face detection and alignment
  -> ArcFace embedding and cosine similarity
  -> liveness fusion
  -> deepfake probability fusion
  -> optional instruction verification
  -> GRANT or DENY
```

Decision thresholds in `backend/app/config.py`:

| Signal | Threshold | Meaning |
| --- | ---: | --- |
| Face confidence | `0.70` | YuNet detection must be reliable. |
| Similarity | `0.40` | ArcFace cosine similarity must match the stored template. |
| Liveness | `0.70` | Fused liveness score must be high enough. |
| Deepfake probability | `0.30` | Scores above this are treated as synthetic risk. |
| Instruction confidence | `0.60` | Challenge instructions must be detected confidently. |

## Architecture

```text
React/Vite frontend
  |  multipart HTTP via Axios
  v
FastAPI backend
  |-- API routes and rate limiting
  |-- AuthPipeline decision engine
  |-- AI model modules
  |-- AES/JWT security helpers
  `-- SQLAlchemy data access
          |
          v
       SQLite database
```

Core backend modules:

- `app/main.py`: FastAPI application, route definitions, request decoding, audit logging.
- `app/pipeline.py`: Orchestrates detection, recognition, liveness, deepfake checks, and final decisions.
- `app/models/detector.py`: YuNet detection, face quality validation, pose heuristics, alignment.
- `app/models/recognizer.py`: ArcFace ONNX embedding extraction and template comparison.
- `app/models/liveness.py`: Passive and multi-frame liveness scoring.
- `app/models/deepfake.py`: Hybrid deepfake probability scoring.
- `app/models/anti_injection.py`: Physical camera and virtual-camera checks.
- `app/models/instruction_verifier.py`: MediaPipe-based face and hand challenge verification.
- `app/db/models.py`: SQLite schema for users, auth logs, and challenge logs.
- `app/crypto.py`: AES-256-GCM embedding encryption and RS256 JWT creation.

## API Summary

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Checks server status and pipeline initialization. |
| `POST` | `/api/v1/register` | Registers a username, email, and multiple face frames. |
| `POST` | `/api/v1/authenticate` | Authenticates a single image or extracted frame. |
| `POST` | `/api/v1/authenticate/video` | Authenticates a recorded video. This is the current frontend login path. |
| `GET` | `/api/v1/challenge` | Issues a two-instruction challenge. |
| `POST` | `/api/v1/authenticate/challenge` | Authenticates using two challenge videos. |
| `GET` | `/api/v1/instructions` | Lists available challenge instructions and stats. |
| `GET` | `/api/v1/users/{user_id}/history` | Returns recent authentication attempts for a user. |

## Setup

### Backend

Use Python 3.11 or newer. The checked-in virtual environment appears to use Python 3.13, but some ML packages may be easier to install on Python 3.11 or 3.12.

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:FACE_AUTH_AES_KEY = "0000000000000000000000000000000000000000000000000000000000000000"
$env:PYTHONPATH = "."
uvicorn app.main:app --reload --port 8000
```

Expected health response:

```json
{
  "status": "ok",
  "pipeline_loaded": true
}
```

The first backend request may download or initialize model weights if they are missing from `backend/weights`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually:

```text
http://localhost:5173
```

The Vite proxy forwards `/api` requests to `http://localhost:8000`.

## Example API Calls

Register with five images:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/register `
  -F "username=alice" `
  -F "email=alice@example.com" `
  -F "face_data=@frame1.jpg" `
  -F "face_data=@frame2.jpg" `
  -F "face_data=@frame3.jpg" `
  -F "face_data=@frame4.jpg" `
  -F "face_data=@frame5.jpg"
```

Authenticate with a video:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/authenticate/video `
  -F "username=alice" `
  -F "video=@auth_video.webm"
```

Successful authentication returns `authenticated: true`, score details, processing time, and a `jwt_token`.

## Results and Performance

The repository includes an evaluation script at `backend/training/evaluate.py`, but no dataset-backed benchmark output is committed in the documentation. For that reason, this documentation does not claim fixed accuracy, FAR, FRR, AUC, or latency values.

Current measurable outputs available at runtime:

- Per-attempt liveness score.
- Per-attempt deepfake probability.
- Per-attempt ArcFace similarity.
- Per-attempt processing time in milliseconds.
- Threat flags and denial reason.
- Authentication history stored in SQLite.

To produce reportable metrics, prepare `data/test` and run:

```powershell
cd backend
python -m training.evaluate --data_root data/test --weights_dir weights --model all
```

## Strengths

- Multi-layer defense instead of one-shot face matching.
- Uses lightweight runtime models and CPU-compatible libraries.
- Encrypts biometric templates before storing them.
- Maintains an audit trail for review and debugging.
- Separates frontend capture, API orchestration, AI modules, security helpers, and persistence.
- Includes optional training paths for stronger liveness and deepfake classifiers.

## Limitations

- Runtime metrics depend on camera quality, lighting, device performance, and whether fine-tuned weights are available.
- HTTP upload routes skip physical camera injection checks because they do not receive a live camera handle.
- Single-frame authentication has weaker liveness evidence than video authentication.
- Some challenge instructions are best-effort heuristic checks and can be sensitive to camera framing.
- The runtime deepfake module and training deepfake script use different EfficientNet variants unless integrated further.
- Production deployment would require stronger secret management, HTTPS, migration management, and model validation on representative datasets.

## Project Structure

```text
DSP Project/
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- pipeline.py
|   |   |-- config.py
|   |   |-- crypto.py
|   |   |-- db/
|   |   `-- models/
|   |-- training/
|   |-- requirements.txt
|   `-- Dockerfile
|-- frontend/
|   |-- src/
|   |   |-- api/
|   |   |-- components/
|   |   `-- pages/
|   `-- package.json
|-- docs/
|-- analysis_and_approaches.md
|-- walkthrough.md
`-- README.md
```

## Documentation Map

- `README.md`: main project entry point.
- `walkthrough.md`: practical system walkthrough.
- `analysis_and_approaches.md`: design analysis and current implementation status.
- `docs/PROJECT_OVERVIEW.md`: concise overview for reviewers.
- `docs/ABSTRACT_AND_OBJECTIVES.md`: report-ready abstract and objectives.
- `docs/ARCHITECTURE_USED.md`: architecture and component interaction.
- `docs/AI_MODELS_USED_AND_WHY.md`: model choices and rationale.
- `docs/PROJECT_FLOW.md`: registration and authentication flow.
- `docs/PROJECT_DOCUMENTATION.md`: detailed technical documentation.
- `docs/PROJECT_REPORT_CONTENT.md`: report-style content.
- `docs/PROJECT_PRESENTATION.md`: presentation speaking notes.
- `docs/PPT_PRESENTATION_CONTENT.md`: slide-by-slide content.

## Future Improvements

- Wire the anti-injection guard into a true live camera capture backend path.
- Standardize runtime deepfake weights with the training script outputs.
- Add automated tests for API routes, threshold decisions, and database logging.
- Add dataset-backed benchmark tables for FAR, FRR, EER, AUC, and latency.
- Add a migration tool such as Alembic for database schema evolution.
- Add Docker Compose for backend, frontend, and persistent volume setup.
- Add model cards describing training data, limitations, and bias risks.
- Add secure production secret handling instead of default development keys.

## Latest Documentation Expansion - 2026-04-11

The latest repository state adds an optional VLM hybrid authentication track alongside the original frame/video pipeline. The original documentation above remains valid for the traditional route; the new documents below expand it without replacing existing content.

New and expanded documentation:

- `docs/LATEST_CHANGES_2026_04_11.md`: concise summary of the latest VLM, frontend, backend, storage, and caveat updates.
- `docs/VLM_HYBRID_AUTHENTICATION.md`: VLM registration, VLM authentication, model selection, fusion, and fallback behavior.
- `docs/API_REFERENCE.md`: traditional, challenge, history, and VLM endpoint reference with request and response shapes.
- `docs/FRONTEND_AND_USER_FLOWS.md`: browser routes, React pages, recording durations, and score display behavior.
- `docs/DATABASE_AND_STORAGE.md`: SQLite tables, encrypted embeddings, VLM reference-frame storage, and backup notes.
- `docs/SETUP_AND_OPERATIONS.md`: local setup, optional VLM setup, environment variables, smoke tests, and operational notes.
- `docs/SECURITY_PRIVACY_LIMITATIONS.md`: security controls, privacy-sensitive data, limitations, and hardening tasks.
- `docs/EVALUATION_AND_REPORTING.md`: safe reporting guidance and benchmark workflow.

Latest code-aware additions now documented:

- `VLMRegister` and `VLMLogin` frontend pages.
- `/api/v1/vlm/register`, `/api/v1/vlm/authenticate`, and `/api/v1/vlm/status`.
- `VLMAuthPipeline`, `VLMReasoner`, and VLM model auto-selection.
- `vlm_registrations` metadata table and `data/vlm_ref_frames/{user_id}` storage.
- Optional VLM dependencies in `backend/vlm_requirements.txt`.
- Conservative VLM behavior: traditional pipeline runs first, VLM only reasons after a traditional grant, and VLM failure falls back to the traditional path.

Current working-tree note: the VLM registration backend route currently expects repeated `face_data` image files, while `VLMRegister.jsx` sends a `video` upload. The docs now call this out explicitly so the integration contract can be aligned before a VLM browser demo.

## Additional Deep Documentation And Interactive Presentation

The second documentation expansion adds a deeper model explanation, complete system flow reference, and a static animated presentation.

New files:

- `docs/AI_MODELS_DETAILED_DEEP_DIVE.md`: detailed explanation of YuNet, ArcFace, MobileNetV3 liveness, rPPG, deepfake detection, MediaPipe challenges, VLM reasoning, and decision fusion.
- `docs/COMPLETE_SYSTEM_FLOW_DETAILED.md`: full flow from browser camera capture to backend models, storage, logging, JWT response, and frontend result display.
- `docs/SLIDE_DECK_SCRIPT_AND_ANIMATION_GUIDE.md`: slide-by-slide presenter script, animation explanation, Q and A preparation, and demo checklist.
- `docs/interactive_auth_presentation/`: standalone animated HTML/CSS/JavaScript presentation.

Open the interactive presentation directly:

```text
docs/interactive_auth_presentation/index.html
```
