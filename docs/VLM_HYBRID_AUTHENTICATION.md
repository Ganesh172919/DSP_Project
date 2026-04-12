# VLM Hybrid And Pure Authentication

Repository: [Ganesh172919/DSP_Project](https://github.com/Ganesh172919/DSP_Project)

This document explains the VLM layer used by:

- Hybrid VLM authentication
- Pure VLM authentication

The VLM layer is additive. It does not remove the original pipeline. In hybrid mode it acts as a second visual judge after the traditional pipeline. In pure mode it becomes the main decision-maker.

## Why The VLM Layer Exists

The traditional pipeline produces strong numeric evidence:

- face confidence
- ArcFace similarity
- liveness score
- deepfake score
- optional challenge score

The VLM adds semantic reasoning on top of that. It compares reference frames and authentication frames and explains whether the same person is visible, whether the subject looks live, and whether the scene looks authentic or spoofed.

## Implemented Modes

### Hybrid VLM

```text
uploaded auth video
  -> traditional AuthPipeline
  -> if DENY, stop
  -> if GRANT, load VLM reference frames
  -> run VLM reasoning
  -> fuse traditional and VLM scores
  -> optional VLM veto
```

### Pure VLM

```text
stored VLM reference frames
  -> uploaded auth video or auth frames
  -> run VLM reasoning directly
  -> same_person + is_live + is_authentic + overall_score
  -> GRANT or DENY
```

## Files Involved

| File | Role |
| --- | --- |
| `backend/app/vlm_routes.py` | `/api/v1/vlm/*` endpoints |
| `backend/app/vlm_pipeline.py` | pure VLM pipeline |
| `backend/app/vlm_config.py` | VLM models, thresholds, prompt text, hardware rules |
| `backend/app/models/vlm_reasoner.py` | VLM loading, inference, and output parsing |
| `backend/app/db/vlm_models.py` | VLM registration metadata table |
| `backend/app/db/vlm_crud.py` | save and load VLM reference frames |
| `backend/vlm_requirements.txt` | VLM dependencies |
| `frontend/src/pages/VLMRegister.jsx` | VLM registration page |
| `frontend/src/pages/VLMLogin.jsx` | hybrid VLM page |
| `frontend/src/pages/PureVLMLogin.jsx` | pure VLM page |

## VLM Registration

Endpoint:

```text
POST /api/v1/vlm/register
```

Current request contract:

| Field | Type | Description |
| --- | --- | --- |
| `username` | string | unique username |
| `email` | string | unique email |
| `face_data` | repeated image files | registration frames |

Backend behavior:

1. validate username and email
2. decode uploaded registration frames
3. run traditional registration to build the encrypted ArcFace template
4. store VLM reference frames on disk
5. store VLM registration metadata in SQLite

## Hybrid VLM Authentication

Endpoint:

```text
POST /api/v1/vlm/authenticate
```

Request fields:

| Field | Type | Description |
| --- | --- | --- |
| `username` | string | existing user |
| `video` | file | authentication recording |
| `auth_frames` | optional repeated image files | explicit VLM auth frames |

Hybrid backend flow:

1. load user and decrypt ArcFace template
2. run the traditional video pipeline
3. if the traditional result is `DENY`, skip VLM
4. if the traditional result is `GRANT`, load stored VLM reference frames
5. extract or read VLM authentication frames
6. run VLM reasoning
7. fuse traditional and VLM confidence
8. let the VLM veto when the denial is strong enough
9. return reasoning, scores, red flags, and final decision

## Pure VLM Authentication

Endpoint:

```text
POST /api/v1/vlm/authenticate/pure
```

Request fields:

| Field | Type | Description |
| --- | --- | --- |
| `username` | string | existing VLM-registered user |
| `video` | file | authentication recording |
| `auth_frames` | optional repeated image files | explicit VLM auth frames |

Pure VLM backend flow:

1. load stored VLM reference frames
2. extract or read authentication frames
3. run the VLM only
4. grant access only if same person, live, authentic, and above threshold

## Stronger Prompt Rules

The prompt sent to the VLM is now stricter for both hybrid and pure modes.

The model is told to deny when it sees:

- a mobile phone or tablet
- a laptop screen, monitor, or TV
- a printed photo or paper face
- a picture, poster, or replayed video
- a face inside another screen, playback window, or rectangle
- a face hidden behind a device
- frozen eye state across authentication frames
- missing full-face visibility

The model is also told:

- grant only when the live user's full face is the main subject in the camera frame
- keep `overall_score` very low when spoof evidence is present
- output JSON only
- include explicit red flags for device-based or replay-based attacks

## Prompt Output Contract

The VLM returns:

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

## Model Selection

Supported values in `VLM_MODEL`:

| Value | Meaning |
| --- | --- |
| `auto` | choose based on hardware |
| `qwen` | force Qwen2.5-VL-3B-Instruct |
| `moondream` | force moondream2 |
| `smolvlm` | force SmolVLM-256M-Instruct |
| `disabled` | disable VLM reasoning |

## Fusion And Veto

Hybrid fusion:

```text
final_confidence = 0.60 * traditional_confidence + 0.40 * vlm_overall_score
```

The VLM can veto a traditional `GRANT` when:

- same person is false, or
- live is false, or
- authentic is false, and
- the deny signal is strong enough

## Fallback Behavior

If the VLM cannot load or inference fails, the reasoner returns a neutral judgment so the traditional system does not crash.

Neutral fallback behavior:

- `same_person = true`
- `is_live = true`
- `is_authentic = true`
- confidence values around `0.5`

## Operational Caveats

- VLM inference is slower than the traditional path.
- The first VLM request may download large models.
- VLM reference frames are stored on disk.
- VLM reasoning is useful but not a forensic guarantee.
- Stricter prompts reduce false acceptance risk, but they can also increase false rejections when framing is poor.
