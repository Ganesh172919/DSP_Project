# Project Presentation

## Presentation Title

AI-Based Facial Authentication with Liveness and Deepfake Protection

## Short Introduction

This project is a secure face authentication system that verifies not only who the user is, but also whether the submitted face appears live and non-synthetic. It combines a web camera interface, FastAPI backend, encrypted biometric storage, and a multi-layer AI pipeline.

## Problem Statement For Presentation

Traditional face login can be fooled by:

- Printed photos.
- Mobile screen replays.
- Recorded videos.
- Virtual camera feeds.
- AI-generated or face-swapped faces.

The project solves this by adding liveness and deepfake checks around the face recognition process.

## Key Points To Highlight

- The system is full-stack: React frontend plus FastAPI backend.
- Registration captures five frames for a stable face template.
- Authentication uses a short video for temporal analysis.
- YuNet detects and aligns the face.
- ArcFace extracts a 512-dimensional identity embedding.
- Liveness detection checks texture, color, moire patterns, movement, and pulse-like signals.
- Deepfake detection checks spectral artifacts, CNN features, boundary artifacts, reflections, skin uniformity, color correlation, and flicker.
- Stored face embeddings are encrypted with AES-256-GCM.
- Successful authentication returns an RS256 JWT.
- All attempts are logged for review.

## Architecture Explanation

The browser captures images or video and sends them to the FastAPI backend. The backend runs an `AuthPipeline` that calls separate modules for detection, recognition, liveness, deepfake detection, optional challenge verification, encryption, and database logging. The final response is a clear grant or deny decision with scores.

## Methodology Explanation

The system follows this order:

1. Capture face input.
2. Detect and align the face.
3. Extract ArcFace embedding.
4. Compare with stored encrypted template.
5. Compute liveness score.
6. Compute deepfake probability.
7. Optionally verify active instructions.
8. Apply final decision thresholds.

## Innovation Angle

The main innovation is layered authentication. Instead of depending only on a face similarity score, the system requires agreement from multiple security signals. This makes the design more robust and easier to explain during review.

## Academic Value

This project combines:

- Digital signal processing ideas such as FFT and rPPG.
- Computer vision for detection, alignment, and landmarks.
- Deep learning for embeddings and CNN features.
- Cybersecurity concepts such as spoofing, replay, encryption, JWTs, and audit logs.
- Full-stack software engineering.

## Honest Limitations To Mention

- Dataset-backed benchmark values are not committed yet.
- Camera and lighting conditions affect liveness signals.
- Fine-tuned liveness and deepfake weights are optional.
- Anti-injection checking is implemented but skipped for uploaded file routes.
- Production deployment would require stronger secret management and HTTPS.

## Closing Statement

The project demonstrates a practical and explainable approach to secure facial authentication by combining identity matching with liveness verification, deepfake analysis, encrypted storage, and auditable decisions.

## Latest Presentation Add-On: VLM Hybrid Reasoning

Add this point if presenting the latest version:

The project now includes an optional VLM-enhanced authentication path. After the traditional pipeline grants access, a Vision Language Model compares registration reference frames with the current authentication frames. It checks whether the same person appears present, whether the authentication attempt looks live, and whether there are signs of spoofing or manipulation. It returns both scores and a natural-language explanation.

Good slide talking points:

- VLM registration stores selected reference frames in addition to the encrypted ArcFace template.
- VLM login runs the traditional pipeline first and invokes VLM only after a traditional grant.
- Final confidence combines traditional and VLM scores.
- High-confidence VLM concerns can override a traditional grant.
- If VLM is unavailable, the system falls back to the traditional pipeline.
