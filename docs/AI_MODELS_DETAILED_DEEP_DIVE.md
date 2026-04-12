# AI Models Detailed Deep Dive

This document gives a detailed explanation of every AI, computer-vision, and signal-processing model used in the facial authentication system. It expands the shorter model summary documents and is intended for project reports, viva preparation, implementation review, and presentation scripting.

## 1. Model Stack At A Glance

The system does not depend on one model to decide authentication. It uses a layered model stack where each layer answers a different security question.

| Layer | Module | Main model or method | Question answered |
| --- | --- | --- | --- |
| Layer 0 | `AntiInjectionGuard` | camera metadata, virtual-device signatures, PRNU-like variance | Does the input appear to come from a physical camera? |
| Layer 1 | `FaceDetector` | OpenCV YuNet ONNX | Is there a valid face, and where are its landmarks? |
| Layer 2 | `FaceRecognizer` | ArcFace `w600k_r50.onnx` through ONNX Runtime | Does the face match the registered identity? |
| Layer 3 | `LivenessDetector` | MobileNetV3-Small features, texture, color, moire, optical flow, micro-movement, rPPG | Does the face appear live? |
| Layer 4 | `DeepfakeDetector` | FFT, EfficientNet-B0 features, boundary, reflection, texture, color, flicker | Does the face appear synthetic or manipulated? |
| Layer 5 | `InstructionVerifier` | MediaPipe FaceMesh and Hands | Did the user perform a fresh requested action? |
| Optional VLM | `VLMReasoner` | Qwen2.5-VL-3B-Instruct or moondream2 | Do reference and authentication frames look like the same live authentic person? |

The important design idea is separation of concerns. Face recognition alone only answers identity similarity. Liveness and deepfake modules answer whether the input is trustworthy. The challenge module answers whether the user can respond to a fresh prompt. The VLM layer adds semantic reasoning and explanation.

## 2. Layer 0: Anti-Injection Guard

### Purpose

The anti-injection layer is designed to detect whether the camera source appears to be a real physical camera or a virtual/injected stream.

### Runtime File

```text
backend/app/models/anti_injection.py
```

### Inputs

- A live `cv2.VideoCapture` object, or
- a camera index that the backend can open.

### Outputs

```text
InjectionResult(
  is_real_camera: bool,
  confidence: float,
  flags: list[str]
)
```

### Techniques Used

#### Camera Enumeration

The module checks operating-system camera listings and compares names against known virtual camera signatures:

- OBS Virtual Camera
- ManyCam
- DroidCam
- EpocCam
- XSplit VCam
- Snap Camera
- v4l2loopback
- related names from `VIRTUAL_CAMERA_SIGNATURES`

This helps catch virtual camera devices before any face processing begins.

#### PRNU-Like Sensor Noise Check

Real camera sensors have tiny differences in pixel response. This is called photo response non-uniformity, or PRNU. The implementation samples several frames, converts them to grayscale, computes pixel-wise variance, and compares the mean variance against `PRNU_VARIANCE_THRESHOLD`.

The idea:

```text
real sensor -> tiny natural noise changes -> higher variance
virtual feed -> overly uniform generated frames -> lower variance
```

#### Metadata And Frame Heuristics

The module also checks:

- whether resolution is a standard webcam resolution
- whether FPS is suspiciously exact
- whether sharpness is unnaturally uniform across center and corners
- whether rolling-shutter-like row variation is absent

### Current Route Limitation

The browser upload endpoints skip anti-injection because uploaded files do not expose the live camera device handle. The module is implemented, but it becomes most useful when the backend controls the live camera capture path.

## 3. Layer 1: YuNet Face Detection And Alignment

### Purpose

The detector finds a face, validates its quality, extracts five landmarks, estimates simple pose, and aligns the crop to ArcFace geometry.

### Runtime File

```text
backend/app/models/detector.py
```

### Model

```text
face_detection_yunet_2023mar.onnx
```

The model is downloaded from OpenCV Zoo when missing.

### Why YuNet Was Chosen

- Lightweight ONNX model.
- Works through OpenCV `cv2.FaceDetectorYN`.
- Provides bounding boxes and five landmarks.
- Runs on CPU.
- Avoids heavy detector dependencies.
- Gives the exact landmarks needed for ArcFace alignment.

### Input

An OpenCV BGR frame:

```text
height x width x 3
```

### Output

```text
DetectionResult(
  face_detected: bool,
  face_confidence: float,
  detection: FaceDetection | None,
  rejection_reason: str | None
)
```

`FaceDetection` contains:

- bounding box
- five landmarks
- confidence
- aligned `112 x 112` face crop
- yaw estimate
- pitch estimate
- face area ratio

### Detection Validation

The detector rejects faces when:

| Check | Config |
| --- | --- |
| Confidence too low | `FACE_CONFIDENCE_THRESHOLD = 0.70` |
| Face too small | `MIN_FACE_AREA_RATIO = 0.05` |
| Yaw too large | `MAX_YAW_DEGREES = 30.0` |
| Pitch too large | `MAX_PITCH_DEGREES = 20.0` |

This prevents poor crops from entering ArcFace and downstream liveness checks.

### Landmark Order

YuNet returns five landmarks:

1. eye center
2. eye center
3. nose tip
4. mouth corner
5. mouth corner

The detector maps these landmarks into the ArcFace reference order and applies a similarity transform.

### Alignment

ArcFace expects a canonical face crop. The detector uses:

```text
cv2.estimateAffinePartial2D(source_landmarks, reference_landmarks)
cv2.warpAffine(image, transform, (112, 112))
```

Alignment matters because ArcFace embeddings assume consistent eye, nose, and mouth positions. Without alignment, the embedding changes more with head pose and crop position.

## 4. Layer 2: ArcFace Face Recognition

### Purpose

ArcFace converts the aligned face crop into a 512-dimensional identity embedding.

### Runtime File

```text
backend/app/models/recognizer.py
```

### Runtime Model

```text
w600k_r50.onnx
```

The model is extracted from the InsightFace `buffalo_l` package when missing.

### Why ArcFace Was Chosen

- Strong identity representation based on angular-margin learning.
- Produces compact 512-dimensional embeddings.
- Works well with cosine similarity.
- ONNX Runtime makes inference portable.
- It is a standard choice for face verification.

### Preprocessing

The aligned BGR face is transformed as follows:

```text
BGR -> RGB
uint8 -> float32
normalize pixel values to [-1, 1]
HWC -> CHW
add batch dimension
```

The final tensor shape is:

```text
1 x 3 x 112 x 112
```

### Embedding Extraction

ArcFace produces a 512-dimensional vector. The system L2-normalizes it:

```text
embedding = embedding / ||embedding||
```

When both registration and authentication embeddings are normalized, their dot product is cosine similarity.

### Registration Template Construction

Registration does not store one raw frame. It averages embeddings from accepted aligned faces:

```text
frame_1 -> embedding_1
frame_2 -> embedding_2
...
template = mean(embedding_i)
template = L2_normalize(template)
```

This reduces noise caused by blink, blur, and small pose changes.

### Authentication Matching

Authentication computes:

```text
similarity = dot(authentication_embedding, stored_template)
```

The threshold is:

```text
SIMILARITY_THRESHOLD = 0.40
```

If similarity is below threshold, the decision engine returns `identity_mismatch`.

### Storage

The template is not stored as plaintext. It is encrypted with AES-256-GCM and stored in `users.embedding_enc`.

## 5. Layer 3: Liveness Detection

### Purpose

The liveness layer estimates whether the face appears to belong to a live person in front of the camera rather than a printed photo, display replay, or other spoof.

### Runtime File

```text
backend/app/models/liveness.py
```

### Core Signals

The liveness detector combines:

- MobileNetV3-Small CNN feature analysis.
- Moire pattern detection.
- Texture analysis.
- Color distribution analysis.
- Face boundary analysis.
- Optical flow when video frames are available.
- Micro-movement when landmark sequences are available.
- rPPG pulse signal when enough frames are available.
- Optional instruction compliance score.

### MobileNetV3-Small Feature Analysis

If fine-tuned weights exist:

```text
weights/liveness_mobilenetv3.pth
```

the model is loaded as a direct liveness classifier.

If fine-tuned weights do not exist, MobileNetV3-Small is used as an ImageNet feature extractor. The implementation analyzes feature statistics:

- channel variance
- spatial non-uniformity
- high-frequency energy
- activation sparsity

The intuition:

```text
real skin -> varied texture and rich feature activations
printed/screen spoof -> flatter or more regular feature patterns
```

### Moire Detection

Screens can introduce periodic interference patterns. The moire check:

1. Converts the aligned face to grayscale.
2. Applies a Hanning window.
3. Computes FFT magnitude.
4. Removes the DC center.
5. Counts unusually strong spectral peaks.

High periodic peak ratio indicates possible screen replay.

### Texture Analysis

Texture analysis uses Laplacian variance, gradient diversity, and high-frequency energy. Real skin has natural micro-texture. Printed photos and screen displays can be too smooth or too regular.

### Color Distribution

The system checks HSV and YCrCb color distributions. Real skin generally has moderate saturation and chrominance diversity. Printed or displayed faces often shift these distributions.

### Optical Flow

When video frames are available, Farneback optical flow estimates movement between frames.

The detector looks for:

- natural small movement
- enough variation across frames
- not completely static
- not excessively shaky

Photo attacks tend to be too static. Some replays may move, but movement can be unnaturally uniform.

### Micro-Movement

When landmark sequences are available, the system tracks small landmark changes. Live faces often show involuntary jitter and tiny pose changes. Static spoofs do not.

### rPPG

rPPG stands for remote photoplethysmography. It tries to detect a pulse-like signal from green-channel intensity changes in forehead regions.

The process:

1. Extract forehead ROIs from face landmarks.
2. Track average green-channel intensity over time.
3. Bandpass filter the signal.
4. Compute FFT.
5. Look for a peak in the heart-rate range.

Configured ranges:

| Parameter | Value |
| --- | --- |
| `RPPG_MIN_BPM` | `45.0` |
| `RPPG_MAX_BPM` | `180.0` |
| `RPPG_BANDPASS_LOW` | `0.75 Hz` |
| `RPPG_BANDPASS_HIGH` | `3.0 Hz` |

rPPG is useful but sensitive to lighting, frame rate, compression, and motion.

### Liveness Fusion

The detector computes a final fused liveness score and compares it with:

```text
FUSION_FINAL_THRESHOLD = 0.70
```

If final liveness is below threshold, authentication is denied with `liveness_fail`.

## 6. Layer 4: Deepfake Detection

### Purpose

The deepfake layer estimates whether the face appears synthetic, manipulated, or face-swapped.

### Runtime File

```text
backend/app/models/deepfake.py
```

### Signals

The detector combines:

- FFT spectral analysis.
- EfficientNet-B0 feature analysis.
- Face boundary artifacts.
- Eye reflection consistency.
- Skin texture uniformity.
- RGB channel correlation.
- Temporal flicker.

### FFT Spectral Analysis

Generative models can leave frequency artifacts from upsampling or synthesis. The spectral analyzer:

1. Converts the aligned face to grayscale.
2. Resizes to `128 x 128`.
3. Applies a Hanning window.
4. Computes FFT.
5. Creates radial frequency bands.
6. Measures spectral decay, high-frequency ratio, and roughness.

Real images usually have smoother natural frequency falloff. Synthetic images can show bumps or abnormal high-frequency energy.

### EfficientNet-B0 Feature Analysis

If fine-tuned weights exist:

```text
weights/deepfake_efficientnet.pth
```

the model can run as a direct classifier.

Otherwise EfficientNet-B0 is used as an ImageNet feature extractor. The module analyzes:

- spatial feature variance
- channel activation diversity
- feature gradient smoothness

Over-smooth generated faces can have more uniform feature activations than real camera captures.

### Boundary Artifacts

Face swaps may show blending issues near face boundaries. The module creates an elliptical face mask and compares boundary gradients with interior gradients. Strong boundary discontinuity is suspicious.

### Eye Reflection Consistency

Real eyes usually have reflections from the same physical light sources. The module compares bright highlight behavior between approximate left and right eye regions. Missing or inconsistent reflections increase risk.

### Skin Uniformity

Deepfakes may over-smooth skin. The module divides the face into zones and checks high-frequency variation. Too-uniform texture increases deepfake probability.

### RGB Channel Correlation

Synthetic images can have abnormal cross-channel correlations. The module computes correlations between RGB channels and flags overly uniform or unusual correlation patterns.

### Temporal Flicker

Real-time deepfakes can flicker frame to frame. With video frames, the module checks intensity changes and oscillation patterns in the face region.

### Deepfake Fusion

The final output is a probability:

```text
0.0 -> likely real
1.0 -> likely synthetic or manipulated
```

Threshold:

```text
DEEPFAKE_FLAG_THRESHOLD = 0.30
```

If deepfake probability is above threshold, authentication is denied with `synthetic_face`.

## 7. Layer 5: Instruction Verification

### Purpose

The instruction verifier checks whether the user performed a fresh requested action. This helps defend against replay attacks because an attacker cannot easily predict the challenge.

### Runtime File

```text
backend/app/models/instruction_verifier.py
```

### Models

- MediaPipe FaceMesh for face landmarks.
- MediaPipe Hands for hand landmarks.

### FaceMesh Outputs

FaceMesh gives dense face landmarks. The verifier uses landmarks to compute:

- eye aspect ratio
- mouth aspect ratio
- head pose
- lip distance
- eyebrow height
- face position in frame
- cheek movement

### Hands Outputs

MediaPipe Hands gives 21 hand landmarks. The verifier uses them to compute:

- finger extended states
- finger count
- hand center
- static gestures
- wave motion
- hand proximity to face regions

### Example Challenge Types

- blink once
- blink multiple times
- wink
- look left or right
- nod
- smile
- mouth open
- raise eyebrows
- show open palm
- show finger count
- wave hand
- touch nose or chin

### Role In Liveness

Instruction verification is one of the strongest replay defenses because the instruction is chosen after the session starts. The result can be included in liveness fusion and final decision logic.

## 8. Optional VLM Reasoning Layer

### Purpose

The VLM layer adds visual reasoning and explanation. It compares registration reference frames with authentication frames and returns structured judgments.

### Runtime Files

```text
backend/app/models/vlm_reasoner.py
backend/app/vlm_config.py
backend/app/vlm_pipeline.py
backend/app/vlm_routes.py
```

### Supported Models

- Qwen2.5-VL-3B-Instruct.
- moondream2.

### Model Selection

The selector checks:

- `VLM_MODEL` environment override.
- CUDA availability.
- GPU VRAM.
- available system RAM.

Qwen is preferred when GPU resources are sufficient. moondream2 is used as a lower-resource fallback.

### VLM Judgment Contract

The VLM returns:

```json
{
  "same_person": true,
  "same_person_confidence": 0.0,
  "is_live": true,
  "liveness_confidence": 0.0,
  "is_authentic": true,
  "authenticity_confidence": 0.0,
  "overall_score": 0.0,
  "reasoning": "text explanation",
  "red_flags": []
}
```

### Fusion

The intended VLM hybrid confidence is:

```text
0.60 * traditional_confidence + 0.40 * vlm_overall_score
```

The VLM may veto a traditional grant if it reports high-confidence concerns.

### Why VLM Helps

The VLM can describe visual evidence in plain language:

- whether facial structure appears consistent
- whether the authentication frame looks live
- whether skin, lighting, reflection, or boundary cues look suspicious
- whether obvious spoofing signs are visible

It is not a replacement for deterministic scoring, but it improves explainability.

## 9. Decision Engine

### Runtime File

```text
backend/app/pipeline.py
```

The decision engine evaluates gates in order:

```text
if injection is not real:
    DENY virtual_camera
if no valid face:
    DENY no_face
if liveness score < 0.70:
    DENY liveness_fail
if deepfake probability > 0.30:
    DENY synthetic_face
if any instruction fails:
    DENY instruction_fail
if similarity < 0.40:
    DENY identity_mismatch
else:
    GRANT
```

### Why This Order Matters

The order is security-oriented:

1. Reject invalid source first.
2. Reject missing/invalid face before expensive matching.
3. Reject spoof risk before identity-only trust.
4. Reject synthetic media.
5. Reject failed fresh challenge.
6. Reject identity mismatch.

## 10. Registration Model Flow

Traditional registration:

```text
browser frames
  -> decode JPEG
  -> YuNet detect
  -> pose and quality checks
  -> 112 x 112 alignment
  -> quick liveness score
  -> ArcFace embedding
  -> average embeddings
  -> L2 normalize template
  -> AES-256-GCM encrypt
  -> SQLite user row
```

VLM registration adds reference-frame storage when the route contract is aligned.

## 11. Authentication Model Flow

Traditional video authentication:

```text
browser video
  -> decode frames
  -> pick middle frame
  -> YuNet detect and align
  -> ArcFace embedding
  -> compare to decrypted template
  -> liveness over aligned face and frames
  -> deepfake risk over aligned face and frames
  -> decision engine
  -> auth log
  -> JWT on grant
```

VLM authentication:

```text
traditional video authentication
  -> if DENY, skip VLM
  -> if GRANT, load reference frames
  -> extract auth frames
  -> VLM judgment
  -> score fusion
  -> optional VLM veto
  -> final response with reasoning
```

## 12. Model Strengths And Weaknesses

| Model | Strength | Weakness |
| --- | --- | --- |
| YuNet | Fast face localization and landmarks | Not a spoof detector |
| ArcFace | Strong identity embeddings | Cannot prove liveness |
| MobileNetV3 liveness | Lightweight and local | Needs calibration and benefits from fine-tuning |
| rPPG | Uses physiological signal | Sensitive to lighting and motion |
| FFT moire/spectral | Good for screen/GAN artifacts | Attack-specific and threshold-sensitive |
| EfficientNet deepfake features | Useful learned visual features | Best with fine-tuned weights |
| MediaPipe challenge | Fresh-response replay defense | Heuristic and depends on landmarks |
| VLM | Explainable semantic reasoning | Slow, hardware-dependent, probabilistic |

## 13. Why The Project Uses Many Models

Biometric security should not rely on one signal. A single face matcher can be fooled by high-quality images. A single liveness score can fail in poor lighting. A single deepfake detector may miss new generation methods. This project uses multiple independent signals so that an attacker must defeat several different checks at the same time.

The system is best explained as evidence fusion:

```text
face detector -> face is usable
ArcFace -> identity matches
liveness -> input behaves like a live capture
deepfake detector -> input does not look synthetic
challenge -> user can respond to a fresh prompt
VLM -> visual reasoning agrees or raises concerns
```

## 14. Reporting Guidance

Do not claim fixed accuracy unless measured on a known dataset. Good report phrasing:

- "The system implements a multi-layer authentication pipeline."
- "The runtime returns per-attempt liveness, deepfake, similarity, and timing scores."
- "Benchmark metrics should be generated using `backend/training/evaluate.py`."
- "The VLM layer improves explainability but is not treated as a standalone forensic detector."

## 15. Presentation Summary

For slides, explain each model as a guard:

1. YuNet opens the gate only when a clear face exists.
2. ArcFace checks whether the face belongs to the enrolled user.
3. Liveness checks whether the face behaves like a live person.
4. Deepfake detection checks whether the face looks generated or manipulated.
5. Instructions check whether the user can react to a fresh challenge.
6. VLM reasoning explains visual consistency in human-readable form.

