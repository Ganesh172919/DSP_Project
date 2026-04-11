# Security, Privacy, And Limitations

This document collects the security controls, privacy-sensitive data flows, and current limitations of the project.

## Security Controls Implemented

| Control | Implementation |
| --- | --- |
| Biometric template encryption | AES-256-GCM encryption before storing ArcFace embeddings. |
| Token issuance | RS256 JWT returned after successful authentication. |
| Rate limiting | SlowAPI rate limiter on sensitive endpoints. |
| CORS | Local development origins only. |
| Audit logging | SQLite `auth_logs` table records decisions, scores, flags, and denial reasons. |
| Multi-layer verification | Face detection, recognition, liveness, deepfake risk, optional instructions, optional VLM reasoning. |

## Threats Addressed

| Threat | Defenses |
| --- | --- |
| Printed photo | Texture, color, moire, liveness, optional challenge, optional VLM reasoning. |
| Screen replay | Moire, temporal checks, optical flow, flicker, optional challenge. |
| Recorded video replay | Video liveness and challenge path; VLM can compare current auth frames with registration references. |
| Deepfake or face swap | FFT, EfficientNet features, boundary checks, eye reflections, skin uniformity, temporal flicker, VLM authenticity reasoning. |
| Similar-looking impostor | ArcFace similarity against encrypted user template plus VLM same-person reasoning when available. |
| Virtual camera | Anti-injection module exists, but upload routes skip true camera-device validation. |

## Sensitive Data

Sensitive data includes:

- Encrypted ArcFace embeddings in `users.embedding_enc`.
- VLM reference JPEG frames under `backend/data/vlm_ref_frames/`.
- Authentication logs with scores, threat flags, and IP addresses.
- JWT signing keys if generated locally.
- VLM model cache files.

## Privacy Notes

- ArcFace embeddings are encrypted before database storage.
- VLM reference frames are currently stored as JPEG files on disk and should be treated as biometric data.
- For production or formal privacy review, encrypt VLM reference frames at rest or store them in a protected object store.
- Do not commit real user databases, reference frames, or generated JWT keys.
- Add retention policies for biometric data and authentication logs before deployment.

## Current Limitations

- No committed benchmark dataset or validated accuracy report exists.
- Thresholds are not calibrated for a specific deployment environment.
- Lighting, camera quality, face pose, and motion blur affect scores.
- HTTP upload endpoints do not expose a live camera handle to the backend, so physical camera validation is skipped.
- VLM reasoning may be slow and depends on model availability and hardware resources.
- VLM output is probabilistic and may be wrong or inconsistent.
- Runtime deepfake detection uses EfficientNet-B0 features while the training script can train EfficientNet-B4 artifacts.
- Challenge verification is heuristic and depends on MediaPipe availability.
- Production deployment requires HTTPS, stronger secret management, database migrations, monitoring, and stricter CORS.

## Known Engineering Risks

- VLM registration should be tested end to end because the current route and storage helper should agree on whether frame storage returns a count or records.
- Docker setup should be retested and aligned with current dependencies before relying on it.
- Source-code comments include encoding artifacts; a later code maintenance pass should clean them.
- Default development AES key must never be used for real deployments.
- Current VLM registration frontend/backend contract is not aligned: the page sends `video`, while the working-tree backend route expects repeated `face_data` images.

## Recommended Hardening

- Encrypt VLM reference frames.
- Add an Alembic migration layer.
- Store VLM auth reasoning in a dedicated audit table when explainability history is needed.
- Add API and decision-engine tests.
- Add dataset-backed calibration and benchmark reports.
- Add production key generation and rotation guidance.
- Add deployment-specific CORS and rate-limit configuration.
- Add clear data deletion workflows for users.
