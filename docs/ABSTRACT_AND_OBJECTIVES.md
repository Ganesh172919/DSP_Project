# Abstract And Objectives

## Abstract

This project presents an AI-based facial authentication system designed to improve the security of face login by combining face recognition with liveness detection, anti-spoofing, and deepfake screening. The system uses a React frontend to capture user face data and a FastAPI backend to process images and videos through a layered AI pipeline. Face detection is performed with OpenCV YuNet, recognition is performed with ArcFace embeddings, and authentication decisions are based on multiple signals including face similarity, liveness score, deepfake probability, and optional challenge-response verification.

The system stores biometric templates as encrypted 512-dimensional embeddings using AES-256-GCM and records authentication attempts in SQLite for auditability. It also includes optional training and evaluation scripts for improving liveness and deepfake models with custom datasets. The project demonstrates how practical biometric authentication can be strengthened against photo attacks, video replay attacks, and AI-generated face attacks.

## Primary Objectives

- Build a working face registration and authentication system.
- Detect and align faces from browser-captured images and videos.
- Extract robust face embeddings using ArcFace.
- Store biometric templates securely through encryption.
- Verify identity using cosine similarity against a registered template.
- Detect spoofing risk through liveness and visual anti-spoofing methods.
- Detect deepfake risk using frequency-domain, CNN-feature, texture, color, reflection, boundary, and temporal cues.
- Return clear authentication decisions with scores, threat flags, and denial reasons.

## Secondary Objectives

- Provide a clean web interface for registration and login.
- Support video-based authentication for stronger multi-frame analysis.
- Include optional instruction challenge workflows for active liveness verification.
- Maintain an audit log of authentication attempts.
- Provide training scripts for fine-tuning liveness and deepfake models.
- Document the architecture, methodology, setup, limitations, and future scope.

## Scope

The project includes:

- Frontend capture and upload workflows.
- Backend API routes.
- AI pipeline orchestration.
- Face detection and recognition.
- Passive and video-based liveness checks.
- Deepfake risk scoring.
- Optional active challenge verification.
- Local SQLite persistence.
- Local development setup and optional training utilities.

The project does not currently include a committed benchmark dataset, production deployment configuration, or production-grade secret management.

## Expected Benefits

- Stronger authentication than password-only or face-match-only systems.
- Reduced risk from simple photo and screen replay attacks.
- Better explainability through separate score outputs.
- Reviewable architecture suitable for academic evaluation.
- Expandable foundation for future production hardening.

## Success Criteria

The system is considered successful when it can:

- Register a user from multiple valid face frames.
- Authenticate the same user from a short video when identity and liveness checks pass.
- Deny access when face detection, liveness, deepfake, instruction, or similarity thresholds fail.
- Return interpretable scores and denial reasons.
- Preserve encrypted biometric data and audit history.
