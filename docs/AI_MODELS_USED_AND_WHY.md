# AI Models Used And Why

## Overview

The system uses a combination of neural models and deterministic computer-vision checks. The core runtime models are lightweight enough for local development while still supporting a realistic multi-layer biometric pipeline.

## Model Summary

| Component | Runtime Model/Method | Purpose |
| --- | --- | --- |
| Face detection | OpenCV YuNet ONNX | Detect face bounding boxes and five landmarks. |
| Face recognition | ArcFace `w600k_r50.onnx` | Extract 512-dimensional identity embeddings. |
| Liveness | MobileNetV3-Small features plus handcrafted checks | Estimate whether the face appears live. |
| rPPG | Green-channel signal analysis | Detect pulse-like signal when enough video frames exist. |
| Active challenge | MediaPipe FaceMesh and Hands | Verify requested face and hand actions. |
| Deepfake | FFT, EfficientNet-B0 features, and handcrafted checks | Estimate synthetic or manipulated face risk. |
| Optional training | MobileNetV3-Small, Spectral MLP, EfficientNet-B4 | Fine-tune liveness and deepfake models on custom datasets. |

## 1. YuNet Face Detector

### Role

YuNet detects the primary face in an image and returns a bounding box, five landmarks, and a confidence score.

### Why YuNet

- Integrated with OpenCV through `cv2.FaceDetectorYN`.
- Lightweight and CPU-friendly.
- Provides landmarks needed for ArcFace alignment.
- Avoids heavy detector dependencies.
- Suitable for real-time or near-real-time webcam use.

### How It Is Used

The detector validates confidence, face size, yaw, and pitch. Accepted detections are aligned to a canonical `112 x 112` crop.

## 2. ArcFace Recognition Model

### Role

ArcFace produces normalized face embeddings that represent identity.

### Runtime Model

The runtime model is `w600k_r50.onnx`, loaded with ONNX Runtime.

### Why ArcFace

- Strong face recognition approach based on angular-margin learning.
- Produces compact 512-dimensional embeddings.
- Works well with cosine similarity.
- ONNX format keeps deployment simpler than framework-specific inference.

### How It Is Used

During registration, embeddings from multiple aligned faces are averaged and normalized. During authentication, the new embedding is compared with the stored encrypted template after decryption.

## 3. MobileNetV3-Small For Liveness

### Role

MobileNetV3-Small provides image features for passive liveness scoring.

### Why MobileNetV3-Small

- Efficient on CPU.
- Available through Torchvision.
- Good feature extractor for texture and high-frequency patterns.
- Can be fine-tuned with the included training script.

### Runtime Behavior

If `weights/liveness_mobilenetv3.pth` exists, the liveness module loads it as a fine-tuned classifier. Otherwise, it uses ImageNet-pretrained features and analyzes feature statistics.

## 4. rPPG Signal Analysis

### Role

rPPG estimates pulse-like variation from the green channel in forehead regions.

### Why rPPG

- Real faces can show subtle color variation from blood flow.
- Printed photos and masks do not produce a natural pulse signal.
- It adds a time-based liveness signal when enough video frames are available.

### Limitation

rPPG depends on lighting, frame rate, video quality, and stable face landmarks.

## 5. MediaPipe FaceMesh And Hands

### Role

MediaPipe is used for optional active challenge verification.

### Why MediaPipe

- Provides dense face landmarks and hand landmarks.
- Runs locally without custom training.
- Enables blink, gaze, head pose, mouth, expression, hand gesture, and hand-to-face checks.

### Runtime Use

The challenge endpoint issues random instructions and verifies the submitted videos against landmark-derived rules.

## 6. Deepfake Runtime Detector

### Runtime Components

- FFT spectral analysis.
- EfficientNet-B0 ImageNet feature analysis.
- Boundary artifact checks.
- Eye reflection consistency.
- Skin texture uniformity.
- RGB channel correlation.
- Temporal flicker when video is available.

### Why A Hybrid Detector

Deepfake artifacts can appear in different ways. A hybrid detector can catch frequency artifacts, texture smoothing, face blending errors, inconsistent reflections, and temporal instability without depending on one model.

## 7. Optional Deepfake Training Models

`backend/training/train_deepfake.py` can train:

- A spectral MLP over FFT features.
- An EfficientNet-B4 binary classifier.

These are training utilities. The current runtime module uses EfficientNet-B0 unless the runtime loader is updated to consume the EfficientNet-B4 artifact.

## Why Multiple Models And Methods Were Used

Biometric security benefits from independent evidence:

- YuNet answers: is there a valid face?
- ArcFace answers: is this the registered identity?
- Liveness checks answer: does the input appear live?
- Deepfake checks answer: does the input appear synthetic or manipulated?
- Challenge verification answers: can the user react to a fresh prompt?

Combining these layers makes the system more robust than face matching alone.

## Important Note On Metrics

The documentation should not claim fixed accuracy values unless produced by the included evaluation script on a known dataset. Runtime scores are available per authentication attempt, but dataset-level benchmark results are not currently committed.

## Latest Addition: Vision Language Model Reasoning

The latest implementation adds an optional VLM reasoning layer for semantic comparison of registration and authentication frames.

### Supported VLMs

| Model | Runtime role | Selection condition |
| --- | --- | --- |
| Qwen2.5-VL-3B-Instruct | Higher-capability multi-image visual reasoning | Preferred when CUDA and enough VRAM are available. |
| moondream2 | Lightweight visual reasoning fallback | Used when CPU or lower-resource execution is needed. |

### Why Add A VLM

Traditional biometric layers produce numeric evidence. The VLM adds qualitative visual reasoning:

- compares face structure across registration and authentication frames
- looks for obvious photo, screen, mask, or manipulation cues
- returns identity, liveness, authenticity, and overall confidence values
- returns natural-language reasoning for the UI

### How It Is Used

The VLM is invoked only after the traditional video pipeline grants access. This keeps the original liveness and deepfake gates as the first line of defense and avoids spending VLM compute on attempts already denied by the numeric pipeline.

### VLM Limits

VLM reasoning is not a replacement for ArcFace, liveness, or deepfake detection. It is a complementary check. It can be slow, hardware-dependent, and probabilistic, so benchmark claims should still be generated with a controlled evaluation set.
