# Project Overview

## Title

AI-Based Facial Authentication System with Liveness and Deepfake Protection

## Overview

This project is a full-stack biometric authentication system that verifies a user's face while also checking whether the submitted camera input appears live, genuine, and non-synthetic. It combines a React frontend, FastAPI backend, SQLite persistence, encrypted biometric storage, and a layered AI pipeline for face detection, face recognition, liveness detection, anti-spoofing, and deepfake screening.

The current frontend supports registration through five captured camera frames and login through a short recorded webcam video. The backend also includes optional challenge-response endpoints that can ask users to perform random face or hand instructions.

## Problem Addressed

Face authentication systems can be vulnerable when they depend only on image similarity. Common attacks include:

- Printed photo spoofing.
- Screen replay attacks.
- Recorded video replay attacks.
- Virtual camera injection.
- AI-generated faces and face swaps.
- Attempts by another person whose face is visually similar.

This project addresses the problem by combining identity verification with liveness and synthetic-media risk checks.

## Proposed Solution

The system uses a multi-layer verification pipeline:

1. Capture image or video input from the browser.
2. Detect and align the face using YuNet.
3. Extract a 512-dimensional ArcFace embedding.
4. Compare the embedding with the encrypted stored template.
5. Compute liveness using CNN features and visual anti-spoofing checks.
6. Estimate deepfake risk from frequency, CNN-feature, texture, color, boundary, reflection, and temporal cues.
7. Optionally verify random active challenges using MediaPipe FaceMesh and Hands.
8. Apply a threshold-based decision engine.
9. Log the attempt and return a JWT on success.

## Key Features

- Multi-frame registration for more stable templates.
- Video-based login for stronger liveness evidence.
- YuNet face detection and ArcFace recognition.
- AES-256-GCM encryption for biometric embeddings.
- RS256 JWT generation for successful authentication.
- SQLite audit logging of authentication decisions and scores.
- Rate limiting on sensitive endpoints.
- Optional instruction challenges with a 200-instruction catalog.
- Training scripts for optional custom liveness and deepfake models.

## Innovation Angle

The project is not only a face recognition demo. Its main innovation is layered verification: the identity score, liveness score, deepfake probability, and optional instruction-compliance score are all evaluated before access is granted. This reduces dependence on any single model and creates a clearer security story for reviewers.

## Expected Use Cases

- Academic demonstration of AI-based biometric security.
- Prototype secure login for web applications.
- Study project for liveness detection and anti-spoofing.
- Foundation for future deployment with calibrated models and production security.

## Outcome

The implemented system can register users, authenticate them through video, deny suspicious attempts based on score thresholds, store encrypted biometric templates, and provide auditable authentication history.
