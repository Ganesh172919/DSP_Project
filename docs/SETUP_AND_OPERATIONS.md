# Setup And Operations

This guide explains how to run the current traditional and VLM-enabled project locally.

## Prerequisites

- Python 3.11 or 3.12 is recommended for the backend.
- Node.js and npm for the frontend.
- A webcam for browser flows.
- Optional CUDA GPU for faster VLM inference.

Python 3.13 may work for parts of the stack, but some ML packages, especially MediaPipe or VLM dependencies, may be easier to install on Python 3.11 or 3.12.

## Backend Setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:FACE_AUTH_AES_KEY = "0000000000000000000000000000000000000000000000000000000000000000"
$env:PYTHONPATH = "."
uvicorn app.main:app --reload --port 8000
```

Health check:

```powershell
curl.exe http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "pipeline_loaded": true
}
```

## Optional VLM Setup

Install VLM dependencies on top of the normal backend environment:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r vlm_requirements.txt
```

Optional model selection:

```powershell
$env:VLM_MODEL = "auto"
```

Supported values:

| Value | Meaning |
| --- | --- |
| `auto` | Pick the best available option based on hardware. |
| `qwen` | Force Qwen2.5-VL-3B-Instruct. |
| `moondream` | Force moondream2. |
| `disabled` | Disable VLM reasoning. |

Check VLM status:

```powershell
curl.exe http://localhost:8000/api/v1/vlm/status
```

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually:

```text
http://localhost:5173
```

## Local Pages To Test

| Page | Purpose |
| --- | --- |
| `http://localhost:5173/register` | Traditional still-frame registration. |
| `http://localhost:5173/login` | Traditional video login. |
| `http://localhost:5173/vlm-register` | VLM video registration. |
| `http://localhost:5173/vlm-login` | VLM hybrid video login. |

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `FACE_AUTH_AES_KEY` | 64 zero characters | AES-256-GCM key as a 64-character hex string. Must be changed outside development. |
| `JWT_PRIVATE_KEY` | `backend/keys/private.pem` | RS256 private key path. |
| `JWT_PUBLIC_KEY` | `backend/keys/public.pem` | RS256 public key path. |
| `VLM_MODEL` | `auto` | VLM model override. |
| `VLM_MAX_RAM_GB` | `5.0` | Soft max RAM target for VLM selection. |
| `PYTHONPATH` | not set | Should include backend root when running modules locally. |

## Important Paths

| Path | Purpose |
| --- | --- |
| `backend/data/auth.db` | SQLite database. |
| `backend/data/vlm_ref_frames/` | VLM reference frame storage. |
| `backend/weights/` | Traditional model weights and optional trained artifacts. |
| `backend/weights/vlm_cache/` | VLM model cache. |
| `backend/keys/` | JWT key files if generated locally. |

## Recommended Manual Smoke Test

1. Start backend.
2. Confirm `/health`.
3. Start frontend.
4. Register a user through `/register`.
5. Log in through `/login`.
6. Check `/api/v1/users/{user_id}/history`.
7. Install VLM dependencies if needed.
8. Check `/api/v1/vlm/status`.
9. Register a second user through `/vlm-register`.
10. Log in through `/vlm-login`.

## Operational Notes

- The first model initialization can be slow.
- VLM model loading can be much slower than traditional inference.
- Browser camera APIs require permission and usually a secure context; localhost is accepted by major browsers.
- Upload routes skip live hardware anti-injection checks.
- Rate limiting is currently `5/minute` on sensitive endpoints.

## Docker Note

The repository includes `backend/Dockerfile`, but it should be treated as a development starting point until retested against the current dependency set. It contains an InsightFace download command while the current recognizer documentation centers on ArcFace ONNX through ONNX Runtime.

## Current VLM Smoke-Test Adjustment

For the current working-tree backend, test VLM registration with repeated `face_data` images rather than a `video` field:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/vlm/register `
  -F "username=alice_vlm" `
  -F "email=alice-vlm@example.com" `
  -F "face_data=@frame1.jpg" `
  -F "face_data=@frame2.jpg" `
  -F "face_data=@frame3.jpg"
```

The browser VLM registration page currently submits a video. Align the route contract before relying on the page for the smoke test.
