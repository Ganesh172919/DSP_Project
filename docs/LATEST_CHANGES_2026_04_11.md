# Latest Changes Documentation - 2026-04-11

This document summarizes the repository state after the latest VLM-oriented changes. It is intended as a quick reviewer guide before reading the deeper architecture, API, setup, and model documents.

## Summary

The project now contains two authentication tracks:

| Track | Frontend pages | Backend endpoints | Main purpose |
| --- | --- | --- | --- |
| Traditional pipeline | `/register`, `/login` | `/api/v1/register`, `/api/v1/authenticate/video` | Register from still frames and authenticate from a short video using numeric model scores. |
| VLM hybrid pipeline | `/vlm-register`, `/vlm-login` | `/api/v1/vlm/register`, `/api/v1/vlm/authenticate`, `/api/v1/vlm/status` | Add video registration, reference-frame storage, and Vision Language Model reasoning on top of the traditional pipeline. |

The original routes remain available. The VLM work is additive: new files, new frontend routes, and a new VLM table were added without replacing the older registration and login path.

## New Backend Capabilities

- `backend/app/vlm_routes.py` adds a FastAPI router mounted under `/api/v1/vlm`.
- `backend/app/vlm_pipeline.py` composes the existing `AuthPipeline` with VLM reasoning.
- `backend/app/models/vlm_reasoner.py` lazy-loads either Qwen2.5-VL-3B-Instruct or moondream2 based on hardware and environment settings.
- `backend/app/vlm_config.py` contains VLM model selection, cache paths, thresholds, fusion weights, and prompt templates.
- `backend/app/db/vlm_models.py` adds the `vlm_registrations` SQLAlchemy table.
- `backend/app/db/vlm_crud.py` stores VLM reference frames on disk and stores metadata in SQLite.
- `backend/vlm_requirements.txt` lists optional VLM dependencies to install on top of the normal backend requirements.
- `backend/notebooks/colab_vlm_auth.ipynb` provides a notebook path for VLM experimentation.

## New Frontend Capabilities

- `frontend/src/App.jsx` now includes navigation links for VLM registration and VLM login.
- `frontend/src/pages/VLMRegister.jsx` records a 5-second registration video and submits it to `/api/v1/vlm/register`.
- `frontend/src/pages/VLMLogin.jsx` records a 5-second authentication video and submits it to `/api/v1/vlm/authenticate`.
- VLM login displays traditional pipeline scores, VLM scores when invoked, VLM model name, VLM reasoning, override state, and reference-frame availability.

## Hybrid Decision Behavior

The VLM pipeline is conservative:

1. Run the existing traditional video authentication pipeline first.
2. If the traditional pipeline denies, return `DENY` and skip VLM inference.
3. If the traditional pipeline grants, extract authentication frames for VLM comparison.
4. Compare stored registration reference frames with current authentication frames.
5. Fuse confidence with `0.60` traditional weight and `0.40` VLM weight.
6. Allow high-confidence VLM concerns to veto a traditional grant.
7. If VLM cannot load or fails, return a neutral VLM result and preserve the traditional decision path.

## Current Storage Additions

Traditional storage remains:

- SQLite database at `backend/data/auth.db`.
- Encrypted 512-dimensional ArcFace embeddings in the `users` table.
- Per-attempt records in `auth_logs`.
- Challenge records in `challenge_logs`.

VLM storage adds:

- `vlm_registrations` table for reference-frame metadata.
- JPEG reference frames on disk under `backend/data/vlm_ref_frames/{user_id}/`.
- VLM model cache under `backend/weights/vlm_cache`.

## Important Runtime Notes

- VLM dependencies are optional. Install `backend/vlm_requirements.txt` only when running the VLM pages or endpoints.
- VLM model loading is lazy. The first VLM status or authentication call may take much longer than later calls.
- `VLM_MODEL` can be set to `auto`, `qwen`, `moondream`, or `disabled`.
- Traditional endpoints skip live camera anti-injection checks because browser uploads do not expose a live `cv2.VideoCapture` device handle to the backend.
- The VLM endpoint currently logs traditional pipeline scores in `auth_logs`; the detailed VLM reasoning is returned in the API response but is not stored in a dedicated VLM auth-log table.

## Implementation Audit Notes

These notes are included so demonstrations and reports stay honest:

- The VLM registration route expects the reference-frame storage helper result to be count-like in some places and collection-like in others. Before using VLM registration in a live demo, verify `/api/v1/vlm/register` end to end and align the route response with `store_vlm_reference_frames()`.
- `backend/Dockerfile` still contains an InsightFace model-download command even though the runtime recognizer is documented around ArcFace ONNX and ONNX Runtime. Treat the Dockerfile as a development starting point until it is tested and aligned with current dependencies.
- Some source comments contain text-encoding artifacts from prior edits. They do not change runtime behavior, but they should be cleaned in a code-focused maintenance pass.

## Current Working-Tree Compatibility Note

The current uncommitted `backend/app/vlm_routes.py` implementation differs from the earlier VLM pipeline wrapper design:

- `POST /api/v1/vlm/register` currently accepts repeated `face_data` images, matching the normal `/api/v1/register` input style, then stores those frames as VLM references.
- `frontend/src/pages/VLMRegister.jsx` currently sends a `video` field to `/api/v1/vlm/register`.
- This means the VLM registration frontend and backend are not aligned in the current working tree. Before a live VLM demo, either update the frontend to send repeated `face_data` frames or update the backend route to accept the 5-second registration video flow again.
- `POST /api/v1/vlm/authenticate` currently uses the base `AuthPipeline` directly and calls `VLMReasoner` directly after a traditional grant, rather than routing through `VLMAuthPipeline.authenticate_vlm()`.
- `backend/app/vlm_config.py` now handles missing `psutil` or `torch` more gracefully by using fallback RAM values and CPU-only assumptions.

## Documentation Added In This Update

- `docs/VLM_HYBRID_AUTHENTICATION.md`
- `docs/API_REFERENCE.md`
- `docs/FRONTEND_AND_USER_FLOWS.md`
- `docs/DATABASE_AND_STORAGE.md`
- `docs/SETUP_AND_OPERATIONS.md`
- `docs/SECURITY_PRIVACY_LIMITATIONS.md`
- `docs/EVALUATION_AND_REPORTING.md`
