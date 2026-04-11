# Project Documentation

## 1. Introduction

This project implements a facial authentication system with anti-spoofing and deepfake protection. It allows a user to register a face template, authenticate using a short video, and receive a grant or deny decision based on identity similarity, liveness, and synthetic-media risk.

## 2. Purpose

The purpose of the project is to demonstrate a secure biometric login workflow that goes beyond simple face matching. The system is designed to reduce risk from printed photos, screen replays, recorded videos, virtual camera sources, and AI-generated faces.

## 3. Technology Stack

| Area | Technologies |
| --- | --- |
| Frontend | React 18, Vite, Axios, React Router |
| Backend | FastAPI, Uvicorn, Python multipart handling |
| Computer vision | OpenCV, NumPy, SciPy |
| AI inference | ONNX Runtime, PyTorch, Torchvision |
| Face detection | OpenCV YuNet ONNX |
| Face recognition | ArcFace `w600k_r50.onnx` |
| Liveness | MobileNetV3-Small features, texture/color checks, rPPG, optical flow |
| Deepfake | FFT, EfficientNet-B0 features, handcrafted artifact checks |
| Challenge verification | MediaPipe FaceMesh and Hands |
| Database | SQLite, SQLAlchemy |
| Security | AES-256-GCM, RS256 JWT, SlowAPI rate limiting |

## 4. Functional Modules

### Frontend Module

The frontend provides:

- Navigation between registration and login.
- Webcam access through browser APIs.
- Five-frame capture for registration.
- Four-second video recording for authentication.
- Score and result display after authentication.

### Backend API Module

The API module provides:

- Registration route.
- Single-frame authentication route.
- Video authentication route.
- Challenge issue and challenge authentication routes.
- Instruction listing route.
- Authentication history route.
- Health check route.

### AI Pipeline Module

The AI pipeline coordinates:

- Optional anti-injection check.
- Face detection and alignment.
- ArcFace embedding extraction.
- Liveness detection.
- Deepfake detection.
- Optional instruction verification.
- Final grant/deny decision.

### Security Module

The security module handles:

- Embedding encryption and decryption.
- JWT creation and verification.
- Rate limiting.
- CORS configuration.
- Authentication audit logging.

### Data Module

The data module stores:

- Registered users.
- Encrypted face embeddings.
- Face quality score.
- Authentication attempts.
- Challenge issue and completion records.

## 5. API Endpoints

### `GET /health`

Returns API status and whether the pipeline is loaded.

Example response:

```json
{
  "status": "ok",
  "pipeline_loaded": true
}
```

### `POST /api/v1/register`

Registers a new user.

Form fields:

- `username`: registered username.
- `email`: registered email.
- `face_data`: one or more image files, with five recommended.

Response fields:

- `user_id`
- `username`
- `liveness_score`
- `face_quality`
- `status`

### `POST /api/v1/authenticate`

Legacy still-image authentication endpoint.

Form fields:

- `username`
- `face_data`

Returns:

- `authenticated`
- `confidence`
- `threat_flags`
- `scores`
- `processing_time_ms`
- `jwt_token` on success
- `denial_reason` on failure

### `POST /api/v1/authenticate/video`

Current frontend login endpoint.

Form fields:

- `username`
- `video`

This endpoint decodes video frames and uses the frame sequence for liveness and deepfake analysis.

### `GET /api/v1/challenge`

Issues a random instruction challenge.

Returns:

- `challenge_id`
- `instructions`
- `ttl_seconds`

### `POST /api/v1/authenticate/challenge`

Authenticates a user with two instruction videos.

Form fields:

- `username`
- `challenge_id`
- `video_1`
- `video_2`

### `GET /api/v1/instructions`

Returns the full instruction catalog and statistics.

### `GET /api/v1/users/{user_id}/history`

Returns recent authentication logs for a user.

## 6. Database Design

### `users`

| Field | Purpose |
| --- | --- |
| `id` | Primary key. |
| `username` | Unique login identifier. |
| `email` | Unique email address. |
| `password_hash` | Optional field; face is primary authentication. |
| `embedding_enc` | AES-256-GCM encrypted 512-dimensional face template. |
| `face_quality` | Average registration detection confidence. |
| `created_at` | Registration timestamp. |

### `auth_logs`

| Field | Purpose |
| --- | --- |
| `user_id` | User associated with the attempt. |
| `timestamp` | Attempt time. |
| `ip_address` | Client IP when available. |
| `liveness_score` | Final liveness score. |
| `deepfake_score` | Final deepfake probability. |
| `similarity_score` | ArcFace cosine similarity. |
| `injection_confidence` | Anti-injection confidence when used. |
| `threat_flags` | JSON array of detected flags. |
| `decision` | `GRANT` or `DENY`. |
| `denial_reason` | Reason for denial. |

### `challenge_logs`

| Field | Purpose |
| --- | --- |
| `challenge_id` | Unique challenge identifier. |
| `user_id` | Completed user, if any. |
| `instruction_ids` | JSON array of issued instruction IDs. |
| `instruction_results` | JSON array of verification results. |
| `created_at` | Issue time. |
| `completed_at` | Completion time. |
| `expired` | Expiry marker. |

## 7. Methodology Details

### Face Detection

The system uses YuNet because it is lightweight, OpenCV-native, and returns landmarks directly. The detector rejects faces that are too small, low-confidence, or outside acceptable pose ranges.

### Face Recognition

ArcFace is used because it produces discriminative identity embeddings. The system stores a normalized average template from multiple registration frames and compares authentication embeddings using cosine similarity.

### Liveness

Liveness is a weighted fusion problem. The system combines single-frame image cues and multi-frame temporal cues, then compares the final score with `0.70`.

### Deepfake Detection

The deepfake module treats the output as a risk probability. It combines spectral, feature, texture, reflection, boundary, color, and temporal evidence. Values above `0.30` are considered suspicious.

### Challenge Verification

The challenge system verifies actions from MediaPipe landmarks. It is designed to make replay attacks harder because the requested action is selected after the authentication session begins.

## 8. Setup

Backend:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:FACE_AUTH_AES_KEY = "0000000000000000000000000000000000000000000000000000000000000000"
$env:PYTHONPATH = "."
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

## 9. Results And Performance

The code records per-attempt scores and processing time. However, no validated dataset benchmark is currently committed. For reportable metrics, run:

```powershell
cd backend
python -m training.evaluate --data_root data/test --weights_dir weights --model all
```

Metrics supported by the evaluation script include AUC-ROC, FAR, FRR, EER, precision, recall, F1, and mean/p95 latency.

## 10. Limitations

- Results depend on lighting, camera quality, and available model weights.
- Upload endpoints cannot fully validate the physical camera source.
- Some MediaPipe challenge checks are heuristic.
- Runtime deepfake detection and training deepfake models need integration alignment.
- Production deployment requires stronger key management and HTTPS.

## 11. Future Improvements

- Add automated tests.
- Add benchmark datasets and documented evaluation results.
- Integrate trained liveness and deepfake artifacts into runtime.
- Add Docker Compose.
- Add Alembic migrations.
- Harden secrets, keys, CORS, and deployment configuration.
- Add model cards and bias evaluation.

## 12. Conclusion

The project demonstrates a practical layered approach to face authentication. It combines identity verification with liveness and deepfake checks, stores biometric templates securely, and provides clear audit information for every authentication attempt.

## 13. Latest VLM Hybrid Documentation

The latest repository state adds an optional VLM hybrid authentication module.

### Added Technology Stack Items

| Area | Technologies |
| --- | --- |
| VLM reasoning | Transformers, Qwen2.5-VL-3B-Instruct, moondream2 |
| VLM hardware detection | PyTorch CUDA checks, psutil RAM checks |
| VLM storage | SQLite metadata plus JPEG reference frames on disk |
| VLM frontend | `VLMRegister.jsx`, `VLMLogin.jsx` |

### Added Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/vlm/register` | Register with 5-second video and store VLM reference frames. |
| `POST` | `/api/v1/vlm/authenticate` | Authenticate with traditional pipeline plus optional VLM reasoning. |
| `GET` | `/api/v1/vlm/status` | Report VLM model and hardware status. |

### Added Database Table

`vlm_registrations` stores the user ID, reference-frame folder path, frame count, average quality, and creation time.

### Added User Flow

The VLM flow records 5-second videos for both registration and login. VLM authentication runs the traditional video pipeline first. If the traditional decision is `GRANT`, the VLM compares stored registration reference frames with current authentication frames and returns structured reasoning.

### Added Documentation Files

Read these for full details:

- `docs/LATEST_CHANGES_2026_04_11.md`
- `docs/VLM_HYBRID_AUTHENTICATION.md`
- `docs/API_REFERENCE.md`
- `docs/FRONTEND_AND_USER_FLOWS.md`
- `docs/DATABASE_AND_STORAGE.md`
- `docs/SETUP_AND_OPERATIONS.md`
- `docs/SECURITY_PRIVACY_LIMITATIONS.md`
- `docs/EVALUATION_AND_REPORTING.md`
