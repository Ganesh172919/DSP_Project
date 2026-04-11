# Database And Storage

The project uses SQLite through SQLAlchemy for local persistence. Biometric embeddings are encrypted before storage. VLM reference frames are stored as JPEG files on disk with metadata in SQLite.

## Main Database

Configured path:

```text
backend/data/auth.db
```

Configured SQLAlchemy URL:

```text
sqlite:///backend/data/auth.db
```

The database is initialized on FastAPI startup through:

- `app.db.models.init_db()`
- `app.db.vlm_models.init_vlm_tables()`

## Tables

### `users`

Stores registered identities.

| Column | Type | Purpose |
| --- | --- | --- |
| `id` | integer | Primary key. |
| `username` | string | Unique login identifier. |
| `email` | string | Unique email address. |
| `password_hash` | string/null | Optional field; face auth is primary in this project. |
| `embedding_enc` | binary | AES-256-GCM encrypted ArcFace template. |
| `face_quality` | float | Average registration detection quality. |
| `created_at` | datetime | Registration timestamp. |

### `auth_logs`

Stores authentication attempts.

| Column | Type | Purpose |
| --- | --- | --- |
| `id` | integer | Primary key. |
| `user_id` | integer/null | Linked user when available. |
| `timestamp` | datetime | Attempt timestamp. |
| `ip_address` | string/null | Client IP address when available. |
| `liveness_score` | float/null | Final liveness score. |
| `deepfake_score` | float/null | Final deepfake probability. |
| `similarity_score` | float/null | ArcFace similarity. |
| `injection_confidence` | float/null | Anti-injection confidence. |
| `threat_flags` | text | JSON array of threat flags. |
| `decision` | string | `GRANT` or `DENY`. |
| `denial_reason` | string/null | Reason for denial. |

### `challenge_logs`

Stores active challenge lifecycle data.

| Column | Type | Purpose |
| --- | --- | --- |
| `challenge_id` | string | Unique issued challenge ID. |
| `user_id` | integer/null | User who completed the challenge. |
| `instruction_ids` | text | JSON array of issued instruction IDs. |
| `instruction_results` | text | JSON array of pass/fail details. |
| `created_at` | datetime | Challenge issue time. |
| `completed_at` | datetime/null | Completion time. |
| `expired` | integer | Expiry marker. |

### `vlm_registrations`

Stores metadata for VLM reference frames.

| Column | Type | Purpose |
| --- | --- | --- |
| `id` | integer | Primary key. |
| `user_id` | integer | User linked to VLM reference frames. Unique and indexed. |
| `frames_dir` | string | Disk folder containing JPEG frames. |
| `frame_count` | integer | Number of frames stored. |
| `avg_quality` | float | Average selected frame quality. |
| `created_at` | datetime | VLM registration timestamp. |

## File Storage

### VLM Reference Frames

Reference frames are stored under:

```text
backend/data/vlm_ref_frames/{user_id}/frame_0.jpg
backend/data/vlm_ref_frames/{user_id}/frame_1.jpg
backend/data/vlm_ref_frames/{user_id}/frame_2.jpg
```

The current implementation stores frames as JPEG files on disk and stores only metadata in the database.

### Model Weights And Cache

Configured model folder:

```text
backend/weights
```

VLM cache folder:

```text
backend/weights/vlm_cache
```

Expected traditional runtime models include:

- `face_detection_yunet_2023mar.onnx`
- `w600k_r50.onnx`
- optional `liveness_mobilenetv3.pth`
- optional `deepfake_efficientnet.pth`

## Encryption Model

ArcFace templates are encrypted with AES-256-GCM before storage:

```text
512-dimensional numpy embedding
  -> serialize to bytes
  -> AES-256-GCM encrypt
  -> store encrypted bytes in users.embedding_enc
```

The AES key comes from:

```text
FACE_AUTH_AES_KEY
```

The development fallback is all zeroes. Production use must override it.

## Data Lifecycle

Traditional registration:

```text
frames -> aligned faces -> embeddings -> averaged template -> encrypted bytes -> users row
```

Traditional authentication:

```text
username -> users row -> decrypt embedding -> run pipeline -> auth_logs row
```

VLM registration:

```text
video -> traditional template -> selected reference frames -> users row + vlm_registrations row + JPEG files
```

VLM authentication:

```text
username -> users row + reference JPEGs -> traditional pipeline -> optional VLM judgment -> auth_logs row
```

## Backup And Reset Notes

For local development, the persistent state is mainly:

- `backend/data/auth.db`
- `backend/data/vlm_ref_frames/`
- `backend/weights/`
- `backend/keys/` if generated

Deleting `auth.db` removes registered users and logs. Deleting `vlm_ref_frames` removes VLM references but does not remove user records.

## Production Considerations

- Add database migrations before production use.
- Encrypt or otherwise protect VLM reference frames at rest.
- Store secrets outside source control.
- Back up the database and reference-frame folder together.
- Add retention rules for authentication logs and biometric artifacts.
- Consider storing VLM reasoning in a dedicated audit table if explainability records are required.

