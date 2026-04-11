# VLM Hybrid Authentication

This document explains the latest Vision Language Model layer added to the facial authentication project. The VLM layer does not replace the original pipeline. It wraps the existing video authentication flow and adds a semantic visual reasoning check after the traditional model stack has already granted access.

## Why The VLM Layer Exists

The original pipeline makes decisions from numeric signals:

- YuNet face confidence.
- ArcFace cosine similarity.
- Liveness fusion score.
- Deepfake probability.
- Optional instruction confidence.

Those scores are useful, but they do not explain visual evidence in natural language. The VLM layer adds a second kind of evidence: comparative reasoning over stored registration frames and current authentication frames.

## Implemented Approach

The implemented approach matches a dual-video VLM strategy:

```text
VLM registration video
  -> extract frames
  -> build normal ArcFace template
  -> select best registration frames
  -> store encrypted embedding plus VLM reference-frame metadata

VLM authentication video
  -> run traditional AuthPipeline
  -> if DENY, skip VLM
  -> if GRANT, compare registration frames and auth frames with VLM
  -> fuse traditional confidence with VLM overall score
  -> optionally let VLM veto a high-risk traditional GRANT
```

## Files Involved

| File | Role |
| --- | --- |
| `backend/app/vlm_routes.py` | Defines `/api/v1/vlm/*` endpoints. |
| `backend/app/vlm_pipeline.py` | Composes the traditional pipeline and VLM judge. |
| `backend/app/vlm_config.py` | Contains VLM model IDs, thresholds, prompt templates, paths, and hardware selection. |
| `backend/app/models/vlm_reasoner.py` | Loads Qwen or moondream and parses structured VLM JSON judgments. |
| `backend/app/db/vlm_models.py` | Adds the `vlm_registrations` metadata table. |
| `backend/app/db/vlm_crud.py` | Stores and loads reference frames from disk. |
| `backend/vlm_requirements.txt` | Optional dependencies for VLM execution. |
| `frontend/src/pages/VLMRegister.jsx` | Browser flow for 5-second VLM registration. |
| `frontend/src/pages/VLMLogin.jsx` | Browser flow for 5-second VLM authentication and reasoning display. |

## VLM Registration

Endpoint:

```text
POST /api/v1/vlm/register
```

Form fields:

| Field | Type | Description |
| --- | --- | --- |
| `username` | string | Unique username. |
| `email` | string | Unique email. |
| `video` | file | 5-second WebM/MP4 camera recording. |

Backend steps:

1. Reject duplicate username or email.
2. Decode uploaded video bytes with OpenCV.
3. Sample frames for normal registration.
4. Run `AuthPipeline.register_face()` to create the ArcFace template.
5. Select the best `VLM_REF_FRAME_COUNT` frames based on face quality.
6. Encrypt and store the ArcFace embedding in the existing `users` table.
7. Store VLM reference frames on disk and metadata in `vlm_registrations`.

Expected response shape:

```json
{
  "user_id": 1,
  "username": "alice",
  "liveness_score": 0.81,
  "face_quality": 0.92,
  "vlm_ref_frames_stored": 3,
  "status": "registered"
}
```

## VLM Authentication

Endpoint:

```text
POST /api/v1/vlm/authenticate
```

Form fields:

| Field | Type | Description |
| --- | --- | --- |
| `username` | string | Existing username. |
| `video` | file | 5-second WebM/MP4 camera recording. |

Backend steps:

1. Load the registered user.
2. Decrypt the stored ArcFace embedding.
3. Load VLM reference frames from disk if they exist.
4. Run the traditional video authentication pipeline.
5. If traditional result is `DENY`, skip VLM and return the denial.
6. If traditional result is `GRANT`, extract authentication frames for VLM input.
7. Ask the VLM for structured JSON with identity, liveness, authenticity, overall score, reasoning, and red flags.
8. Fuse the traditional and VLM scores.
9. Return final grant/deny response with VLM reasoning.
10. Log the final decision to the normal `auth_logs` table.

## VLM Status

Endpoint:

```text
GET /api/v1/vlm/status
```

The status route reports model readiness, selected model, device, load-attempt state, hardware information, and endpoint paths.

## Model Selection

The selector in `backend/app/vlm_config.py` supports:

| Setting | Behavior |
| --- | --- |
| `VLM_MODEL=auto` | Prefer Qwen on sufficient CUDA VRAM, otherwise use moondream when RAM permits. |
| `VLM_MODEL=qwen` | Force Qwen2.5-VL-3B-Instruct. |
| `VLM_MODEL=moondream` | Force moondream2. |
| `VLM_MODEL=disabled` | Disable VLM reasoning. |

Default model IDs:

- `Qwen/Qwen2.5-VL-3B-Instruct`
- `vikhyatk/moondream2`

## Fusion And Veto Rules

Configured weights:

| Signal | Weight |
| --- | ---: |
| Traditional confidence | `0.60` |
| VLM overall score | `0.40` |

The fused confidence is:

```text
final_confidence = 0.60 * traditional_confidence + 0.40 * vlm_overall_score
```

The VLM can veto a traditional grant when:

- VLM reports the person is not the same, not live, or not authentic.
- The VLM deny confidence is at least `VLM_VETO_CONFIDENCE`, currently `0.85`.

If the VLM is concerned but not confident enough to veto, the current implementation grants with caution and returns reasoning.

## Prompt Contract

The VLM prompt asks for JSON only:

```json
{
  "same_person": true,
  "same_person_confidence": 0.0,
  "is_live": true,
  "liveness_confidence": 0.0,
  "is_authentic": true,
  "authenticity_confidence": 0.0,
  "overall_score": 0.0,
  "reasoning": "analysis text",
  "red_flags": []
}
```

The parser accepts direct JSON, JSON inside markdown code fences, or partial JSON-like text with regex fallback.

## Fallback Behavior

If no VLM model can be loaded, or if VLM inference fails, the code returns a neutral VLM judgment:

- `same_person = true`
- `is_live = true`
- `is_authentic = true`
- confidence values around `0.5`
- an error string explaining why VLM was skipped

This is designed to avoid breaking the traditional authentication path on machines without enough VLM resources.

## Operational Caveats

- VLM inference can be slow, especially on CPU.
- The first VLM call may download or load model weights and can take significantly longer.
- VLM reference frames are stored as JPEG files on disk, not encrypted in the current implementation.
- VLM reasoning is returned to the client but not stored in a separate VLM audit table.
- VLM output is a model judgment, not a guaranteed forensic conclusion.

## Current Router Compatibility Note

The current working-tree version of `backend/app/vlm_routes.py` implements VLM registration differently from the video-registration pipeline described above:

- Current backend route: `POST /api/v1/vlm/register` expects repeated `face_data` image files.
- Current VLM registration frontend: `VLMRegister.jsx` sends a `video` field.
- Current backend authentication route: `POST /api/v1/vlm/authenticate` accepts `video` and runs traditional video auth first.
- Current backend VLM reasoning path: the route uses the base `AuthPipeline` and `VLMReasoner` directly instead of calling `VLMAuthPipeline.authenticate_vlm()`.

For a working demo, align one side:

- Frontend-aligned option: change the backend route to accept `video` and call `VLMAuthPipeline.register_face_from_video()`.
- Backend-aligned option: change `VLMRegister.jsx` to capture and send repeated `face_data` frames.

No existing documentation above is removed because both designs exist in the repository: the video-based VLM pipeline exists in `vlm_pipeline.py`, while the current router accepts image frames for VLM registration.
