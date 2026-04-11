# Project Flow

## End-To-End Flow

```text
User
  -> Browser camera
  -> React capture component
  -> Multipart API request
  -> FastAPI route
  -> AuthPipeline
  -> AI model modules
  -> Decision engine
  -> SQLite audit log
  -> JSON response
```

## Registration Flow

```text
Enter username and email
  -> Start camera
  -> Capture 5 JPEG frames
  -> POST /api/v1/register
  -> Decode frames
  -> YuNet detection and alignment per frame
  -> Quick liveness score per accepted face
  -> ArcFace embedding per accepted face
  -> Average embeddings
  -> L2-normalize template
  -> AES-256-GCM encrypt template
  -> Store user in SQLite
  -> Return user_id, liveness_score, face_quality, status
```

## Authentication Flow

```text
Enter username
  -> Record 4-second webcam video
  -> POST /api/v1/authenticate/video
  -> Load registered user
  -> Decrypt stored embedding
  -> Decode video frames
  -> Select middle frame for identity
  -> YuNet detection and alignment
  -> ArcFace embedding extraction
  -> Cosine similarity comparison
  -> Liveness fusion over aligned face and video frames
  -> Deepfake probability fusion over aligned face and video frames
  -> Threshold-based decision
  -> Log auth attempt
  -> Return grant/deny response
```

## Optional Challenge Flow

```text
GET /api/v1/challenge
  -> Backend selects random face and hand instructions
  -> Client records one video per instruction
  -> POST /api/v1/authenticate/challenge
  -> Decode videos
  -> Verify instructions with MediaPipe landmarks
  -> Run identity, liveness, and deepfake checks
  -> Include instruction scores in decision
  -> Store challenge result
```

## Decision Flow

```text
Start
  |
  v
Camera/source check available?
  |
  v
Face detected with sufficient quality?
  |
  v
Liveness score >= 0.70?
  |
  v
Deepfake probability <= 0.30?
  |
  v
Required instructions passed?
  |
  v
ArcFace similarity >= 0.40?
  |
  v
Grant access and issue JWT
```

Any failed gate produces a denial reason and threat flag where applicable.

## Main Denial Reasons

| Reason | Meaning |
| --- | --- |
| `virtual_camera` | The camera source did not appear physical. |
| `no_face` | No acceptable face was detected. |
| `liveness_fail` | Liveness score was below threshold. |
| `synthetic_face` | Deepfake probability was above threshold. |
| `instruction_fail` | A required active challenge was not verified. |
| `identity_mismatch` | ArcFace similarity was below threshold. |
| `no_frames` | The uploaded video could not be decoded into frames. |

## Why This Flow Is Effective

- Registration averages multiple frames instead of relying on one image.
- Authentication uses video to support temporal liveness analysis.
- Identity matching is separated from liveness and deepfake checks.
- Decisions are explainable through individual scores and flags.
- Audit logs preserve evidence for later review.
