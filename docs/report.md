# Project Report

## Abstract

DeepShield Guardian is a webcam-based biometric authentication platform designed to resist contemporary spoofing and deepfake threats without requiring specialized depth or infrared sensors. The system combines browser-side facial and hand landmark extraction, server-side encrypted biometric templates, passive presentation-attack detection, challenge-response liveness verification, geometric face matching, and risk-weighted decision fusion. The implementation uses a React frontend, FastAPI orchestration layer, PostgreSQL persistence, Redis-ready session infrastructure, and dedicated microservice stubs for face analysis and synthetic-media risk scoring. The design prioritizes fail-secure decisions, auditable outcomes, extensibility toward ONNX-served production models, and alignment with current biometric presentation attack detection practices. This repository is not presented as a certified PAD engine; rather, it is a production-oriented engineering scaffold that demonstrates how layered controls can substantially outperform naive face-recognition-only systems and serve as a foundation for academic evaluation, benchmarking, and iterative hardening.

## Table of Contents

1. Introduction
2. Literature Review
3. System Design
4. Implementation
5. Testing and Results
6. Conclusion and Future Work
7. References

## Chapter 1: Introduction

### Problem Statement

Consumer webcams make face authentication accessible, but they also make replay, screen, photo, and deepfake attacks practical. Single-score face recognition is no longer sufficient for high-assurance identity verification.

### Objectives

- Build a full-stack face-authentication platform from scratch
- Add passive PAD and active challenge-response liveness
- Store biometric templates securely
- Produce admin analytics and audit trails
- Create a deployable project package with documentation

### Scope

The implemented system demonstrates architecture, data flow, heuristics, and service boundaries. Formal certification, large-scale model training, and demographic benchmark calibration remain future-work items.

### AI Documentation Companion

The repository now includes an AI-focused documentation set for the recognition, PAD, deepfake, liveness, temporal, and fusion stack:

- `docs/ai-models.md`
- `docs/ai-model-catalog.md`
- `docs/ai-model-appendix.md`

## Chapter 2: Literature Review

Relevant research converges on a layered defense model:

- PAD literature emphasizes texture, moire, boundary, and temporal cues for photo/video spoofing.
- Deepfake detection literature emphasizes frequency-domain artifacts, temporal inconsistency, biological signal absence, and learned forensic features.
- Modern face-recognition systems rely on learned embeddings such as FaceNet and ArcFace, but deployment quality depends on threshold calibration, template protection, and attack-aware orchestration.

## Chapter 3: System Design

### Architecture Summary

- React frontend for capture and user guidance
- FastAPI orchestration service for sessions, policy, and storage
- PostgreSQL for persistent state
- Redis-ready design for short-lived tokens and rate limits
- ML microservice interfaces for face and risk analysis

### Security Design Principles

- Fail-secure policy
- Encrypted templates
- Server-authoritative scoring
- Auditable decision trace
- Extensible model-serving boundary

## Chapter 4: Implementation

### Frontend

- Webcam access via browser media APIs
- MediaPipe Tasks for face and hand landmarks
- Guided registration and authentication flows
- Live quality feedback and challenge sequencing

### Backend

- SQLAlchemy models for users, enrollment sessions, auth attempts, and audit events
- AES-protected template storage using per-user derived keys
- Deterministic geometric embeddings from landmark subsets
- Weighted decision engine and liveness challenge evaluation

### Microservices

- `ml-face`: landmark-to-embedding service stub
- `ml-risk`: frame risk scoring service stub

## Chapter 5: Testing and Results

### Implemented Validation

- Syntax validation for all Python services
- Unit tests for encryption, challenge selection, and decision rules
- Frontend build validation target

### Metrics To Report In A Full Evaluation

- FAR, FRR, EER
- APCER and BPCER
- Per-attack-type detection rates
- Per-demographic accuracy breakdown
- Per-stage latency distributions

## Chapter 6: Conclusion and Future Work

DeepShield Guardian demonstrates a credible architecture for webcam-based biometric authentication hardened against deepfake-era threats. The next step is replacing baseline heuristics with calibrated models and running controlled evaluation across PAD and deepfake benchmark datasets.

Future work:

- ArcFace or FaceNet embedding service
- ONNX Runtime model serving
- rPPG module for passive liveness
- Expanded challenge instrumentation for hand/finger counting
- Formal benchmark evaluation and bias auditing

## References

1. ISO, “ISO/IEC 30107-3:2023 Information technology — Biometric presentation attack detection — Part 3: Testing and reporting,” [https://www.iso.org](https://www.iso.org).
2. ISO, “ISO/IEC 19795 biometric performance testing framework,” [https://www.iso.org](https://www.iso.org).
3. NIST, “Digital Identity Guidelines: Authentication and Lifecycle Management (SP 800-63B),” [https://pages.nist.gov/800-63-4/sp800-63b.html](https://pages.nist.gov/800-63-4/sp800-63b.html).
4. Google AI Edge, “MediaPipe Tasks Vision API,” [https://ai.google.dev/edge/mediapipe](https://ai.google.dev/edge/mediapipe).
5. FastAPI, “FastAPI documentation,” [https://fastapi.tiangolo.com](https://fastapi.tiangolo.com).
6. PostgreSQL Global Development Group, “PostgreSQL documentation,” [https://www.postgresql.org/docs/](https://www.postgresql.org/docs/).
7. Redis, “Redis documentation,” [https://redis.io/docs/latest/](https://redis.io/docs/latest/).
8. A. Ross and A. Jain, “Information fusion in biometrics,” Pattern Recognition Letters, 2003.
9. F. Schroff, D. Kalenichenko, and J. Philbin, “FaceNet: A unified embedding for face recognition and clustering,” CVPR, 2015.
10. J. Deng et al., “ArcFace: Additive angular margin loss for deep face recognition,” CVPR, 2019.
11. A. Rössler et al., “FaceForensics++: Learning to detect manipulated facial images,” ICCV, 2019.
12. Y. Li et al., “Celeb-DF: A large-scale challenging dataset for deepfake forensics,” CVPR, 2020.
13. B. Dolhansky et al., “The Deepfake Detection Challenge dataset,” arXiv, 2020.
14. L. Jiang et al., “DeeperForensics-1.0: A large-scale dataset for real-world face forgery detection,” CVPR, 2020.
15. Z. Wang et al., “CelebA-Spoof: Large-scale face anti-spoofing dataset with rich annotations,” ECCV, 2020.
16. Y. Atoum et al., “Face anti-spoofing using patch and depth-based CNNs,” IJCB, 2017.
17. X. Liu et al., “Multi-modal face anti-spoofing attack detection challenge at CVPR 2019,” CVPR Workshops, 2019.
18. S. Liu et al., “On the effectiveness of vision transformers for zero-shot face anti-spoofing,” 2023.
19. T. de Freitas Pereira et al., “Face liveness detection under bad illumination conditions,” ICIP, 2014.
20. Z. Yu et al., “Searching central difference convolutional networks for face anti-spoofing,” CVPR, 2020.
21. H. Ciftci, I. Demir, and L. Yin, “FakeCatcher: Detection of synthetic portrait videos using biological signals,” TPAMI, 2024.
22. B. Dolhansky et al., “Deepfake detection: current challenges and next steps,” 2022.
23. F. Chollet, “Xception: Deep learning with depthwise separable convolutions,” CVPR, 2017.
24. A. Dosovitskiy et al., “An image is worth 16x16 words: Transformers for image recognition at scale,” ICLR, 2021.
25. S. Marcel et al., “Handbook of Biometric Anti-Spoofing,” Springer, 2019.
26. Microsoft, “ONNX Runtime documentation,” [https://onnxruntime.ai/docs/](https://onnxruntime.ai/docs/).
27. Kubernetes, “Deployments,” [https://kubernetes.io/docs/concepts/workloads/controllers/deployment/](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/).
28. OWASP, “Application Security Verification Standard,” [https://owasp.org/www-project-application-security-verification-standard/](https://owasp.org/www-project-application-security-verification-standard/).
29. European Union, “General Data Protection Regulation,” [https://gdpr.eu/](https://gdpr.eu/).
30. Illinois General Assembly, “Biometric Information Privacy Act,” [https://www.ilga.gov/](https://www.ilga.gov/).
