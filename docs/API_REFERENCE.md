# API Reference

This API reference covers the current traditional, challenge, history, and VLM endpoints exposed by the FastAPI backend.

Base backend URL during local development:

```text
http://localhost:8000
```

Frontend Axios base path:

```text
/api/v1
```

## Health

### `GET /health`

Checks server status and whether the traditional pipeline object has been initialized.

Example response:

```json
{
  "status": "ok",
  "pipeline_loaded": true
}
```

## Traditional Registration

### `POST /api/v1/register`

Registers a new identity from one or more uploaded face images. The frontend sends five captured JPEG frames.

Form data:

| Field | Required | Type | Description |
| --- | --- | --- | --- |
| `username` | yes | string | Unique username. |
| `email` | yes | string | Unique email address. |
| `face_data` | yes | file list | Repeated image file field. Five frames are recommended. |

Example:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/register `
  -F "username=alice" `
  -F "email=alice@example.com" `
  -F "face_data=@frame1.jpg" `
  -F "face_data=@frame2.jpg" `
  -F "face_data=@frame3.jpg" `
  -F "face_data=@frame4.jpg" `
  -F "face_data=@frame5.jpg"
```

Success response:

```json
{
  "user_id": 1,
  "username": "alice",
  "liveness_score": 0.82,
  "face_quality": 0.91,
  "status": "registered"
}
```

Common failures:

| Status | Reason |
| --- | --- |
| `400` | No valid images, no valid face, or registration pipeline validation failure. |
| `409` | Username or email already registered. |
| `500` | Unexpected registration failure. |

## Traditional Authentication

### `POST /api/v1/authenticate`

Legacy endpoint for authenticating with a single uploaded image or video-like file.

Form data:

| Field | Required | Type | Description |
| --- | --- | --- | --- |
| `username` | yes | string | Existing username. |
| `face_data` | yes | file | Image or decodable media upload. |

### `POST /api/v1/authenticate/video`

Current non-VLM frontend login endpoint. It accepts a recorded WebM/MP4 video and uses the full frame sequence for liveness and deepfake checks.

Form data:

| Field | Required | Type | Description |
| --- | --- | --- | --- |
| `username` | yes | string | Existing username. |
| `video` | yes | file | Recorded webcam video. |

Example:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/authenticate/video `
  -F "username=alice" `
  -F "video=@auth_video.webm"
```

Success response shape:

```json
{
  "authenticated": true,
  "confidence": 0.84,
  "threat_flags": [],
  "scores": {
    "liveness": 0.86,
    "deepfake": 0.08,
    "similarity": 0.78,
    "injection": 1.0
  },
  "processing_time_ms": 1420.5,
  "jwt_token": "..."
}
```

Failure responses include `authenticated: false` and `denial_reason`.

## Challenge Endpoints

### `GET /api/v1/challenge`

Issues two random instructions, usually one face instruction and one hand instruction.

### `POST /api/v1/authenticate/challenge`

Authenticates with two instruction videos tied to a previously issued challenge.

Form data:

| Field | Required | Type | Description |
| --- | --- | --- | --- |
| `username` | yes | string | Existing username. |
| `challenge_id` | yes | string | Challenge returned from `/api/v1/challenge`. |
| `video_1` | yes | file | Video for first instruction. |
| `video_2` | yes | file | Video for second instruction. |

### `GET /api/v1/instructions`

Returns the instruction catalog and summary stats for testing and debugging.

## History

### `GET /api/v1/users/{user_id}/history`

Returns the last 10 authentication attempts for a user, including timestamp, IP address, decision, denial reason, scores, and threat flags.

## VLM Registration

### `POST /api/v1/vlm/register`

Registers a user with a 5-second video and stores both a traditional embedding and VLM reference frames.

Form data:

| Field | Required | Type | Description |
| --- | --- | --- | --- |
| `username` | yes | string | Unique username. |
| `email` | yes | string | Unique email. |
| `video` | yes | file | 5-second webcam video. |

Example:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/vlm/register `
  -F "username=alice_vlm" `
  -F "email=alice-vlm@example.com" `
  -F "video=@reg_video.webm"
```

## VLM Authentication

### `POST /api/v1/vlm/authenticate`

Runs the traditional video pipeline first. If the traditional result grants access, the VLM compares stored registration reference frames with current authentication frames.

Form data:

| Field | Required | Type | Description |
| --- | --- | --- | --- |
| `username` | yes | string | Existing username. |
| `video` | yes | file | 5-second authentication video. |

Response shape:

```json
{
  "authenticated": true,
  "confidence": 0.82,
  "vlm_reasoning": "Natural language explanation from the VLM layer.",
  "vlm_model_used": "qwen2.5-vl-3b",
  "vlm_invoked": true,
  "vlm_override": false,
  "has_vlm_refs": true,
  "scores": {
    "traditional": {
      "liveness": 0.86,
      "deepfake": 0.08,
      "similarity": 0.78,
      "injection": 1.0
    },
    "vlm": {
      "vlm_identity": 0.88,
      "vlm_liveness": 0.80,
      "vlm_authenticity": 0.84,
      "vlm_overall": 0.85
    }
  },
  "threat_flags": [],
  "processing_time_ms": 8200.0,
  "traditional_decision": "GRANT",
  "traditional_confidence": 0.84,
  "jwt_token": "..."
}
```

## VLM Status

### `GET /api/v1/vlm/status`

Reports VLM model readiness, selected model, hardware, and endpoint paths.

## Rate Limits

Sensitive endpoints use the configured `RATE_LIMIT`, currently:

```text
5/minute
```

Rate-limited requests return HTTP `429`.

## Current VLM Registration Contract Note

The current working-tree backend route for `POST /api/v1/vlm/register` expects the same multipart shape as normal registration:

| Field | Required | Type | Description |
| --- | --- | --- | --- |
| `username` | yes | string | Unique username. |
| `email` | yes | string | Unique email. |
| `face_data` | yes | repeated files | Face image files to register and store as VLM reference frames. |

Current backend-compatible example:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/vlm/register `
  -F "username=alice_vlm" `
  -F "email=alice-vlm@example.com" `
  -F "face_data=@frame1.jpg" `
  -F "face_data=@frame2.jpg" `
  -F "face_data=@frame3.jpg" `
  -F "face_data=@frame4.jpg" `
  -F "face_data=@frame5.jpg"
```

The current `VLMRegister.jsx` page still submits a `video` field. That frontend/backend contract should be aligned before using the page for a live VLM registration demo.
