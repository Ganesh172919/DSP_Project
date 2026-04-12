# Complete System Flow Detailed Documentation

This document explains the full system flow from browser camera capture to final authentication response. It covers frontend behavior, backend API routing, model execution, security storage, logging, and VLM hybrid behavior.

## 1. System Overview

The project is a full-stack biometric authentication system.

```text
User
  -> Browser camera
  -> React frontend
  -> Axios multipart request
  -> FastAPI route
  -> AuthPipeline or VLM route
  -> AI model layers
  -> security helpers
  -> SQLite storage and audit log
  -> JSON response
  -> frontend result view
```

The system has two main user experiences:

- traditional registration and login
- VLM-enhanced registration and login

The traditional path is the baseline. The VLM path adds visual reasoning and explanation.

## 2. Frontend Application Flow

Frontend root:

```text
frontend/src/App.jsx
```

The app uses React Router and defines these routes:

| Route | Page | Purpose |
| --- | --- | --- |
| `/` | `Register` | Default traditional registration. |
| `/register` | `Register` | Traditional still-frame registration. |
| `/login` | `Login` | Traditional video login. |
| `/vlm-register` | `VLMRegister` | VLM registration page. |
| `/vlm-login` | `VLMLogin` | VLM login page. |

Axios client:

```text
frontend/src/api/client.js
```

Base URL:

```text
/api/v1
```

The Vite dev server proxies `/api` to the FastAPI backend.

## 3. Traditional Registration User Flow

### User Actions

1. User opens `/register`.
2. User enters full name and email.
3. Browser requests camera permission.
4. User captures multiple face frames.
5. Frontend submits the frames.

### Frontend Data

The request is multipart form data:

```text
username = entered name
email = entered email
face_data = face_0.jpg
face_data = face_1.jpg
face_data = face_2.jpg
face_data = face_3.jpg
face_data = face_4.jpg
```

### Backend Endpoint

```text
POST /api/v1/register
```

### Backend Steps

1. Check whether username exists.
2. Check whether email exists.
3. Decode all images with OpenCV.
4. Reject request if no image decodes.
5. Run `AuthPipeline.register_face()`.
6. Encrypt template.
7. Store user row.
8. Return registration summary.

### Registration Model Pipeline

```text
for each frame:
  YuNet detect face
  validate confidence, size, yaw, pitch
  align face to 112 x 112
  quick liveness score
  ArcFace embedding

average embeddings
L2 normalize template
encrypt template
store template
```

### Registration Response

```json
{
  "user_id": 1,
  "username": "alice",
  "liveness_score": 0.82,
  "face_quality": 0.91,
  "status": "registered"
}
```

## 4. Traditional Authentication User Flow

### User Actions

1. User opens `/login`.
2. User enters username.
3. Browser requests camera permission.
4. UI records a 4-second WebM video.
5. Frontend submits the video.
6. UI waits for backend model inference.
7. UI displays result and scores.

### Backend Endpoint

```text
POST /api/v1/authenticate/video
```

### Backend Steps

1. Find user by username.
2. Decrypt stored ArcFace template.
3. Read uploaded video bytes.
4. Decode video to frames.
5. Select the middle frame.
6. Detect and align face.
7. Extract ArcFace embedding.
8. Compute similarity.
9. Run liveness checks.
10. Run deepfake checks.
11. Apply decision gates.
12. Log attempt.
13. Return JWT if granted.

### Frame Strategy

The middle frame is used for identity because it usually avoids first-frame camera adjustment and final-frame movement.

The full video is used for liveness and deepfake checks because temporal signals need frame sequences.

## 5. Single Upload Authentication Flow

Endpoint:

```text
POST /api/v1/authenticate
```

This legacy path accepts `face_data` and extracts one frame. It is weaker than video login because it has less temporal liveness evidence.

## 6. Challenge Flow

### Challenge Issue

Endpoint:

```text
GET /api/v1/challenge
```

Backend:

1. Pick two random instructions.
2. Create a challenge ID.
3. Store challenge in memory.
4. Store challenge metadata in SQLite.
5. Return challenge ID, instructions, and TTL.

### Challenge Authentication

Endpoint:

```text
POST /api/v1/authenticate/challenge
```

Form fields:

```text
username
challenge_id
video_1
video_2
```

Backend:

1. Validate challenge exists.
2. Check TTL.
3. Load user.
4. Decrypt template.
5. Decode both videos.
6. Verify instructions.
7. Run identity, liveness, and deepfake checks.
8. Include instruction score in decision.
9. Store challenge result.
10. Log authentication attempt.

## 7. VLM Hybrid Flow

### VLM Registration Design

Intended video-based VLM registration:

```text
record 5-second video
  -> decode frames
  -> sample frames
  -> normal registration template
  -> select best reference frames
  -> store embedding and reference frames
```

Current working-tree route note:

```text
/api/v1/vlm/register currently expects repeated face_data images.
VLMRegister.jsx currently sends video.
```

This contract should be aligned before a browser-based VLM registration demo.

### VLM Authentication

Endpoint:

```text
POST /api/v1/vlm/authenticate
```

Flow:

```text
load user
decrypt template
run traditional video authentication
if DENY:
  return denial and skip VLM
if GRANT:
  load reference frames
  extract authentication frames
  run VLM reasoner
  fuse confidence
  optionally apply VLM veto
  return final result
```

## 8. Backend Startup Flow

FastAPI startup:

```text
init_db()
init_vlm_tables()
pipeline = AuthPipeline()
include VLM router
```

The traditional pipeline initializes model wrappers, but heavy model loading is mostly lazy.

## 9. Data Security Flow

Registration:

```text
ArcFace template
  -> serialize
  -> AES-256-GCM encrypt
  -> users.embedding_enc
```

Authentication:

```text
users.embedding_enc
  -> AES-256-GCM decrypt
  -> numpy embedding
  -> cosine similarity
```

JWT:

```text
GRANT
  -> create RS256 JWT
  -> return jwt_token
```

Audit:

```text
every attempt
  -> auth_logs row
  -> scores, flags, decision, denial reason
```

## 10. Decision Flow In Detail

The decision engine is deterministic once model scores exist.

### Gate 1: Camera Source

If anti-injection is active and camera is not real:

```text
DENY virtual_camera
```

### Gate 2: Face Detection

If no acceptable face is detected:

```text
DENY no_face
```

### Gate 3: Liveness

If liveness score is below `0.70`:

```text
DENY liveness_fail
```

### Gate 4: Deepfake

If deepfake probability is above `0.30`:

```text
DENY synthetic_face
```

### Gate 5: Instruction

If required instruction fails:

```text
DENY instruction_fail
```

### Gate 6: Identity

If ArcFace similarity is below `0.40`:

```text
DENY identity_mismatch
```

### Grant

If all checks pass:

```text
GRANT
issue JWT
```

## 11. Why Video Login Is Stronger Than Image Login

Still image login can support:

- face detection
- ArcFace matching
- single-frame liveness
- single-frame deepfake checks

Video login adds:

- optical flow
- temporal flicker
- possible rPPG
- movement consistency
- better spoof evidence

This is why the frontend login path uses video.

## 12. System Outputs

Traditional successful response includes:

- `authenticated`
- `confidence`
- `threat_flags`
- `scores`
- `processing_time_ms`
- `jwt_token`

Denied response includes:

- `authenticated: false`
- `denial_reason`
- model scores
- threat flags

VLM response adds:

- `vlm_reasoning`
- `vlm_model_used`
- `vlm_invoked`
- `vlm_override`
- `has_vlm_refs`
- VLM score object
- traditional decision summary

## 13. End-To-End Mental Model

Think of the system as a courtroom:

```text
YuNet says: there is a valid face.
ArcFace says: this face matches the registered user.
Liveness says: the face behaves like a live capture.
Deepfake detector says: the face does not look synthetic.
Instruction verifier says: the user responded to a fresh challenge.
VLM says: visually, the attempt is consistent and explainable.
Decision engine says: all required evidence passed, so grant access.
```

If any required witness fails, access is denied.

