# PPT Presentation Content

## Slide 1: Title

AI-Based Facial Authentication with Liveness and Deepfake Protection

Subtitle:

Secure biometric login using face recognition, anti-spoofing, and synthetic-media detection.

## Slide 2: Problem Statement

- Basic face recognition can be fooled by fake inputs.
- Attackers may use printed photos, screen replays, recorded videos, virtual cameras, or AI-generated faces.
- A secure system must verify both identity and authenticity of the captured input.

## Slide 3: Project Objective

- Build a working face registration and login system.
- Detect and align faces from camera input.
- Verify identity using ArcFace embeddings.
- Detect liveness and deepfake risk.
- Store biometric templates securely.
- Return explainable authentication decisions.

## Slide 4: Proposed Solution

- React frontend captures frames and videos.
- FastAPI backend runs a layered AI pipeline.
- YuNet detects and aligns faces.
- ArcFace verifies identity.
- Liveness and deepfake modules evaluate spoofing risk.
- Encrypted embeddings and audit logs protect biometric data.

## Slide 5: System Architecture

```text
Browser camera
  -> React frontend
  -> FastAPI backend
  -> AuthPipeline
  -> AI modules
  -> SQLite and JWT response
```

## Slide 6: Registration Flow

- User enters username and email.
- Frontend captures five face frames.
- Backend detects and aligns faces.
- ArcFace embeddings are extracted.
- Embeddings are averaged into one template.
- Template is encrypted with AES-256-GCM.
- User is stored in SQLite.

## Slide 7: Authentication Flow

- User enters username.
- Frontend records a 4-second video.
- Backend extracts video frames.
- Middle frame is used for identity matching.
- Full frame sequence supports liveness and deepfake checks.
- Decision engine grants or denies access.

## Slide 8: AI Models Used

- YuNet: face detection and landmarks.
- ArcFace: 512-dimensional face embeddings.
- MobileNetV3-Small: passive liveness features.
- MediaPipe: optional face and hand challenge landmarks.
- EfficientNet-B0 features: runtime deepfake analysis.
- FFT/rPPG/CV checks: spoof and synthetic artifact detection.

## Slide 9: Liveness And Anti-Spoofing

- Texture analysis.
- Color distribution checks.
- Moire pattern detection.
- Optical flow and movement checks.
- Micro-movement checks.
- rPPG pulse-like signal estimation.
- Optional active instruction challenges.

## Slide 10: Deepfake Detection

- FFT spectral anomaly analysis.
- CNN feature anomaly analysis.
- Boundary artifact detection.
- Eye reflection consistency.
- Skin uniformity analysis.
- RGB channel correlation.
- Temporal flicker in video.

## Slide 11: Security Features

- AES-256-GCM encrypted face embeddings.
- RS256 JWT after successful authentication.
- Rate limiting on sensitive endpoints.
- SQLite audit logs for every attempt.
- Threat flags and denial reasons.

## Slide 12: Results And Evaluation

- Runtime returns liveness, deepfake, similarity, and timing scores.
- Audit history stores decisions and threat flags.
- Evaluation script supports AUC, FAR, FRR, EER, F1, and latency.
- Dataset-backed benchmark values should be generated before final numeric claims.

## Slide 13: Limitations

- Results depend on lighting and camera quality.
- Fine-tuned model weights are optional.
- Upload routes skip physical camera anti-injection checks.
- Production deployment needs HTTPS and stronger secret handling.

## Slide 14: Future Scope

- Add benchmark datasets and documented metrics.
- Integrate fine-tuned liveness and deepfake models.
- Add automated tests.
- Add Docker Compose deployment.
- Improve live-camera anti-injection integration.
- Add model cards and privacy documentation.

## Slide 15: Conclusion

The system demonstrates secure facial authentication through layered AI verification, encrypted biometric storage, and explainable decisions.

## Optional Latest Slides: VLM Hybrid Extension

### Slide 16: VLM Hybrid Authentication

- Adds a Vision Language Model reasoning layer.
- VLM registration records a 5-second video.
- Selected registration frames are stored as references.
- VLM login compares registration frames with authentication frames.
- The original traditional pipeline still runs first.

### Slide 17: VLM Decision Fusion

- Traditional pipeline checks face match, liveness, and deepfake risk.
- If traditional pipeline denies, VLM is skipped.
- If traditional pipeline grants, VLM checks same person, liveness, and authenticity.
- Final confidence combines traditional confidence and VLM overall score.
- VLM can veto a grant when it finds high-confidence concerns.

### Slide 18: Latest System Value

- Numeric AI scores provide measurable security signals.
- VLM reasoning adds human-readable explanation.
- The hybrid approach improves presentation value and reviewer understanding.
- The fallback design keeps the original pipeline usable when VLM resources are unavailable.
