# Facial Authentication System Walkthrough

This walkthrough explains how the implemented system works from the user's camera input to the final authentication decision.

## System At A Glance

```text
Browser camera
  -> React registration/login screens
  -> Axios multipart request through Vite proxy
  -> FastAPI route
  -> AuthPipeline
  -> AI/security modules
  -> encrypted SQLite storage and audit logs
  -> JSON decision response
```

The repository contains two major runtime applications:

- `frontend`: React 18 application built with Vite.
- `backend`: FastAPI application with OpenCV, ONNX Runtime, PyTorch, SQLAlchemy, AES encryption, JWT creation, and rate limiting.

## Registration Walkthrough

1. The user opens the registration page.
2. The user enters a username and email.
3. `CameraCapture.jsx` requests browser camera access.
4. The frontend captures five JPEG frames over approximately five seconds.
5. The frames are submitted to `POST /api/v1/register` as repeated `face_data` files.
6. The backend checks whether the username or email already exists.
7. Each valid frame is decoded with OpenCV.
8. `AuthPipeline.register_face()` runs face detection on each frame.
9. `FaceDetector` uses OpenCV YuNet to detect a face, estimate basic pose, and align it to a `112 x 112` ArcFace crop.
10. `LivenessDetector.check_single_frame()` computes a quick liveness score from CNN features, texture, color, and moire checks.
11. `FaceRecognizer` extracts a 512-dimensional ArcFace embedding for every accepted aligned crop.
12. Embeddings are averaged and L2-normalized into one stable template.
13. `crypto.encrypt_embedding()` encrypts the template using AES-256-GCM.
14. SQLAlchemy stores the user record in SQLite with encrypted embedding bytes and face-quality metadata.
15. The response returns the user ID, username, average liveness score, average face quality, and `registered` status.

## Video Authentication Walkthrough

1. The user opens the login page.
2. The user enters a registered username.
3. The frontend records a 4-second WebM webcam video.
4. The video is submitted to `POST /api/v1/authenticate/video`.
5. The backend loads the user by username.
6. The stored encrypted embedding is decrypted with AES-256-GCM.
7. `AuthPipeline.authenticate_video()` decodes video bytes into OpenCV frames.
8. The middle frame is selected for face detection and identity matching.
9. YuNet detects and aligns the face.
10. ArcFace extracts a new 512-dimensional embedding.
11. Cosine similarity is computed against the stored template.
12. The full video frame list is passed to liveness checks.
13. The aligned face and video frames are passed to deepfake checks.
14. The decision engine evaluates thresholds in order.
15. A successful result returns `authenticated: true`, confidence, scores, processing time, threat flags, and a JWT token.
16. Failed results return `authenticated: false` and a denial reason such as `no_face`, `liveness_fail`, `synthetic_face`, or `identity_mismatch`.
17. Every attempt is written to the `auth_logs` table.

## Optional Challenge Walkthrough

The backend includes an active challenge path, although the current main frontend login page uses video authentication without challenges.

1. `GET /api/v1/challenge` picks two random instructions, usually one face instruction and one hand instruction.
2. The challenge is stored in memory and in the `challenge_logs` table.
3. The client records one video per instruction.
4. `POST /api/v1/authenticate/challenge` submits the username, challenge ID, and both videos.
5. `InstructionVerifier` uses MediaPipe FaceMesh and MediaPipe Hands when available.
6. Face instructions are verified from landmark-derived metrics such as eye aspect ratio, head pose, mouth aspect ratio, lip distance, eyebrow height, and face position.
7. Hand instructions are verified from 21-point hand landmarks, finger state, gesture classification, and hand-to-face distance.
8. Instruction confidence becomes part of liveness fusion and the final decision.

## AI Pipeline Layers

### Layer 0: Anti-Injection Guard

The anti-injection module can validate a live `cv2.VideoCapture` source by combining:

- OS camera enumeration.
- Known virtual-camera driver signatures.
- Sensor-noise variance checks.
- Frame metadata heuristics.

Current upload endpoints skip this layer because uploaded files do not expose live camera device metadata.

### Layer 1: Face Detection And Alignment

Implemented by `backend/app/models/detector.py`.

- Model: OpenCV YuNet ONNX.
- Output: bounding box, five landmarks, confidence.
- Quality checks: confidence, face area, yaw, pitch.
- Alignment: similarity transform to ArcFace reference landmarks.

### Layer 2: Face Recognition

Implemented by `backend/app/models/recognizer.py`.

- Model: ArcFace `w600k_r50.onnx`.
- Inference engine: ONNX Runtime.
- Embedding: 512-dimensional, L2-normalized.
- Match score: cosine similarity.
- Runtime authentication path compares against the specific user's encrypted stored template.

### Layer 3: Liveness Detection

Implemented by `backend/app/models/liveness.py`.

Signals include:

- MobileNetV3-Small feature analysis, or fine-tuned weights if present.
- Texture analysis.
- Color distribution checks.
- FFT moire detection.
- Boundary checks.
- Optical flow for multi-frame input.
- Micro-movement analysis when FaceMesh landmarks are available.
- rPPG pulse estimation when enough video frames are available.
- Optional instruction score for challenge login.

### Layer 4: Deepfake Detection

Implemented by `backend/app/models/deepfake.py`.

Signals include:

- FFT spectral anomaly score.
- EfficientNet-B0 ImageNet feature analysis, or fine-tuned `deepfake_efficientnet.pth` if present.
- Boundary artifact score.
- Eye reflection mismatch score.
- Skin uniformity score.
- RGB color correlation score.
- Temporal flicker score for video input.

### Layer 5: Instruction Verification

Implemented by `backend/app/models/instruction_verifier.py`.

This layer is used by the challenge authentication endpoint. It verifies face and hand actions from MediaPipe landmarks.

## Decision Logic

```text
if camera source is not real:
    DENY virtual_camera
if face is missing or too weak:
    DENY no_face
if liveness score < 0.70:
    DENY liveness_fail
if deepfake probability > 0.30:
    DENY synthetic_face
if any required instruction fails:
    DENY instruction_fail
if ArcFace similarity < 0.40:
    DENY identity_mismatch
else:
    GRANT
```

## Backend API

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Confirms the API is running and the pipeline is initialized. |
| `POST /api/v1/register` | Registers a user with multiple face images. |
| `POST /api/v1/authenticate` | Legacy single-frame authentication. |
| `POST /api/v1/authenticate/video` | Video-based authentication used by the current frontend. |
| `GET /api/v1/challenge` | Issues a random challenge. |
| `POST /api/v1/authenticate/challenge` | Verifies challenge videos and authenticates the user. |
| `GET /api/v1/instructions` | Returns instruction definitions and stats. |
| `GET /api/v1/users/{user_id}/history` | Returns recent authentication attempts. |

## Setup And Run

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:FACE_AUTH_AES_KEY = "0000000000000000000000000000000000000000000000000000000000000000"
$env:PYTHONPATH = "."
uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Optional Training Commands

Fine-tune liveness:

```powershell
cd backend
python -m training.train_liveness --data_root data/liveness --epochs 30
```

Train deepfake models:

```powershell
cd backend
python -m training.train_deepfake --data_root data/deepfake --model both --epochs 25
```

Evaluate models:

```powershell
cd backend
python -m training.evaluate --data_root data/test --weights_dir weights --model all
```

## Implementation Notes

- The project is CPU-compatible, but model initialization and inference are faster with GPU-compatible PyTorch/ONNX Runtime where configured.
- Runtime deepfake detection uses EfficientNet-B0; the training script can produce EfficientNet-B4 artifacts that require integration before runtime use.
- The current frontend login flow uses `/authenticate/video`, not the challenge endpoints.
- No committed benchmark table is available, so results should be produced with local evaluation data before reporting numeric accuracy.

## VLM Hybrid Walkthrough Addendum

The latest version adds two VLM pages and three VLM backend endpoints.

### VLM Registration Walkthrough

1. The user opens `/vlm-register`.
2. The user enters a username and email.
3. The browser records a 5-second webcam video.
4. The frontend sends the video to `POST /api/v1/vlm/register`.
5. The backend decodes the video into frames.
6. `VLMAuthPipeline.register_face_from_video()` samples frames for the existing registration pipeline.
7. The existing pipeline creates the encrypted ArcFace template.
8. The VLM pipeline selects the best reference frames by face quality.
9. The backend stores the user in `users`, stores metadata in `vlm_registrations`, and writes reference JPEGs under `backend/data/vlm_ref_frames/{user_id}/`.
10. The frontend displays registration status, face quality, liveness score, and reference-frame count.

### VLM Login Walkthrough

1. The user opens `/vlm-login`.
2. The user enters a registered username.
3. The browser records a 5-second webcam video.
4. The frontend sends the video to `POST /api/v1/vlm/authenticate`.
5. The backend loads the user, decrypts the embedding, and loads VLM reference frames if present.
6. The traditional `AuthPipeline.authenticate_video()` runs first.
7. If the traditional result is `DENY`, the endpoint returns denial and skips VLM inference.
8. If the traditional result is `GRANT`, authentication frames are extracted for VLM comparison.
9. `VLMReasoner` asks Qwen or moondream for structured JSON judgment.
10. `VLMAuthPipeline` fuses traditional and VLM scores. The reasoning logic applies an ultra-strict verification protocol (Device/Media Check, Full Frame Depth, and Eye Blink Check) that automatically denies entry if a phone, tablet, or display is detected.
11. The response includes final decision, traditional scores, VLM scores, VLM reasoning, model used, override status, and JWT or denial reason.

More detail is documented in `docs/VLM_HYBRID_AUTHENTICATION.md`.

### Current Route Contract Note

The VLM walkthrough above describes the video-based VLM registration design that exists in `VLMAuthPipeline`. The current working-tree `vlm_routes.py` registration endpoint accepts repeated `face_data` images instead. The current `VLMRegister.jsx` page still submits `video`, so that frontend/backend contract should be aligned before a browser-based VLM registration demo.
