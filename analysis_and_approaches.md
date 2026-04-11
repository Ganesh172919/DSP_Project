# Analysis And Approaches

This document records the current implementation state, the architectural choices made in the repository, and practical next steps for improving the facial authentication system.

## Current Implementation Status

### Implemented Runtime Capabilities

- React/Vite frontend for registration and login.
- Five-frame registration from browser camera.
- Four-second video authentication from browser camera.
- FastAPI backend with multipart upload endpoints.
- SQLite database with SQLAlchemy models for users, auth logs, and challenge logs.
- AES-256-GCM encryption for stored face embeddings.
- RS256 JWT creation for successful authentication.
- OpenCV YuNet face detection and five-point alignment.
- ArcFace `w600k_r50.onnx` embeddings through ONNX Runtime.
- Liveness fusion from CNN features, handcrafted texture/color checks, moire detection, movement cues, and rPPG where available.
- Runtime deepfake scoring from FFT, EfficientNet-B0 features, boundary artifacts, eye reflections, skin uniformity, color correlation, and temporal flicker.
- Optional MediaPipe-based challenge verification for face and hand instructions.
- Training scripts for optional fine-tuned liveness and deepfake models.

### Important Accuracy Boundaries

The system contains real model inference and real signal analysis, but the repository does not include a committed benchmark report. Any claim about accuracy, FAR, FRR, EER, AUC, or latency must be generated with `backend/training/evaluate.py` on a known dataset.

The current runtime deepfake detector uses EfficientNet-B0 feature analysis. The deepfake training script trains EfficientNet-B4 and a spectral MLP, but those artifacts are not automatically used by the runtime detector without additional integration.

The HTTP upload authentication paths skip the anti-injection guard because uploaded files do not expose camera driver metadata. The guard is still useful for a future backend-owned live camera capture mode.

## Threat Model

The project addresses the following attack categories:

| Attack | Current Defenses |
| --- | --- |
| Printed photo | Face texture, color distribution, moire, liveness fusion, optional active challenge. |
| Screen replay | Moire detection, optical flow consistency, temporal checks, liveness fusion. |
| Recorded video replay | Identity match plus liveness and temporal checks; challenge path can reduce replay success. |
| Virtual camera injection | Anti-injection module exists, but upload endpoints currently skip live device validation. |
| AI-generated face | Spectral, CNN-feature, boundary, eye reflection, skin uniformity, color, and temporal deepfake signals. |
| Face mismatch | ArcFace cosine similarity against encrypted registered template. |

## Methodology Used In This Repository

### Registration

Registration uses multi-frame template construction:

1. Capture five webcam frames.
2. Detect and align faces using YuNet.
3. Reject invalid frames with no face, low confidence, small face area, or excessive pose.
4. Run quick liveness checks on accepted aligned faces.
5. Extract ArcFace embeddings.
6. Average embeddings and L2-normalize the template.
7. Encrypt the template with AES-256-GCM.
8. Store the encrypted bytes in SQLite.

This approach is stronger than single-image registration because it reduces noise from blink, motion blur, and slight pose changes.

### Authentication

Video authentication uses the middle video frame for identity and all frames for time-based checks:

1. Decode uploaded WebM/MP4 bytes into frames with OpenCV.
2. Select the middle frame for face detection and ArcFace matching.
3. Compute cosine similarity against the stored template.
4. Run liveness checks using the aligned face and frame sequence.
5. Run deepfake checks using the aligned face and frame sequence.
6. Evaluate thresholds in a deterministic decision engine.
7. Log the full result and return a JWT on success.

## Approach Evaluation

### Approach A: Lightweight Heuristic Pipeline

This approach uses YuNet, ArcFace, handcrafted liveness cues, and handcrafted deepfake cues.

Strengths:

- Simple to run on CPU.
- Low operational complexity.
- No large custom datasets required for baseline behavior.
- Good for academic demonstrations and transparent explanation.

Limitations:

- Heuristic thresholds may not generalize across cameras and environments.
- Adversarially designed spoofs can bypass simple cues.
- Benchmark claims require a dedicated evaluation set.

### Approach B: Hybrid CNN Plus Landmark Pipeline

This is the approach mostly implemented in the repository. It combines pretrained CNN feature analysis, OpenCV signal processing, MediaPipe landmarks, rPPG, and optional challenge verification.

Strengths:

- Balances implementation feasibility and defense depth.
- Uses independent signals rather than a single model.
- Supports real-time-ish behavior on normal hardware.
- Can become stronger when fine-tuned weights are added.

Limitations:

- More moving parts than a simple face matcher.
- MediaPipe availability can vary by Python version and platform.
- Runtime and training model variants should be standardized for production.

### Approach C: End-To-End Deep Model Pipeline

This approach would use large dedicated anti-spoofing and deepfake models, possibly transformers or specialized face anti-spoof networks.

Strengths:

- Best potential accuracy with enough data.
- Can learn complex attack patterns.
- Better suited for production after validation.

Limitations:

- Requires large curated datasets.
- Higher compute and model management cost.
- Less interpretable for academic review unless accompanied by ablation studies.

## Recommended Direction

The best path is to keep the current hybrid architecture and improve it in layers:

1. Stabilize the implemented runtime pipeline.
2. Add repeatable API and decision-engine tests.
3. Add benchmark datasets and report scripts.
4. Integrate fine-tuned liveness weights into runtime.
5. Align runtime deepfake model loading with the EfficientNet-B4 training output or revise the training script to match EfficientNet-B0.
6. Add a true live-camera backend mode if anti-injection is a formal requirement.
7. Document measured results only after evaluation on controlled data.

## Component Analysis

### Face Detection

YuNet is a strong fit for this project because it is lightweight, OpenCV-native, gives five landmarks directly, and supports fast CPU inference. Its landmarks are sufficient for ArcFace alignment without adding MTCNN, RetinaFace, or InsightFace detector dependencies.

### Face Recognition

ArcFace is appropriate because it produces discriminative normalized embeddings and supports cosine similarity matching. The `w600k_r50.onnx` model is loaded directly with ONNX Runtime, which avoids the heavier InsightFace Python package at runtime.

### Liveness

The liveness system is deliberately multi-signal. Single-frame liveness alone is weak, so the video authentication path adds optical flow, possible rPPG, micro-movement, and temporal signals. Challenge verification is the strongest replay defense when enabled, because a static photo or old video cannot reliably perform a freshly selected instruction.

### Deepfake Detection

The deepfake system focuses on artifacts commonly introduced by generation and face-swap pipelines:

- Frequency-domain irregularities.
- Over-smooth or abnormal CNN feature distributions.
- Face boundary blending.
- Eye reflection inconsistencies.
- Unnaturally uniform skin.
- Abnormal RGB channel correlation.
- Temporal flicker across frames.

These checks are useful for a baseline system, but should be validated against modern deepfake datasets before making production claims.

## File-Level Notes

| File | Purpose |
| --- | --- |
| `backend/app/main.py` | HTTP API, request parsing, response construction, audit logging. |
| `backend/app/pipeline.py` | Central orchestration and final decision logic. |
| `backend/app/config.py` | Thresholds, paths, security settings, device selection. |
| `backend/app/crypto.py` | Embedding encryption and JWT handling. |
| `backend/app/models/detector.py` | YuNet detection, face validation, alignment. |
| `backend/app/models/recognizer.py` | ArcFace embedding extraction and template matching. |
| `backend/app/models/liveness.py` | Liveness checks and score fusion. |
| `backend/app/models/deepfake.py` | Deepfake checks and probability fusion. |
| `backend/app/models/anti_injection.py` | Virtual camera and camera-source validation. |
| `backend/app/models/instruction_verifier.py` | MediaPipe-based active challenge verification. |
| `backend/app/instructions.py` | Static instruction catalog. |
| `backend/training/*.py` | Optional training and evaluation utilities. |
| `frontend/src/pages/Register.jsx` | Registration page and five-frame upload. |
| `frontend/src/pages/Login.jsx` | Video login page and result display. |
| `frontend/src/components/CameraCapture.jsx` | Reusable still-frame camera capture. |
| `frontend/src/components/InstructionChallenge.jsx` | Challenge video capture component. |

## Practical Improvements

- Add API tests for registration validation, duplicate user handling, authentication denial reasons, and history logging.
- Add unit tests for threshold decisions in `AuthPipeline.decide()`.
- Record a small local evaluation set for live, photo, screen replay, and deepfake samples.
- Export evaluation results into a Markdown table committed under `docs/`.
- Fix documentation/code encoding artifacts in source comments when code editing is allowed.
- Replace the development AES key with environment-specific secrets outside source control.
- Add production deployment guidance for HTTPS, CORS, rate limits, key rotation, and database persistence.

## Open Engineering Risks

- Model threshold calibration is environment-dependent.
- MediaPipe may be unavailable or unstable on some Python versions.
- Runtime route behavior differs from camera-owned anti-injection assumptions.
- Fine-tuned model artifacts are optional and may not exist in a clean checkout.
- The committed SQLite database and keys should be treated as development artifacts, not production secrets.
