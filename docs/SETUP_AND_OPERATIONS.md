# Setup And Operations

Repository: [Ganesh172919/DSP_Project](https://github.com/Ganesh172919/DSP_Project)

This guide covers the current local and Docker setup for the traditional, hybrid VLM, and pure VLM flows.

For the folder-by-folder breakdown, see `docs/FOLDER_STRUCTURE_AND_RUN_GUIDE.md`.

## Prerequisites

- Python `3.11` or `3.12`
- Node.js and npm
- Docker Desktop if you want the containerized setup
- Webcam access in the browser
- Optional CUDA GPU for faster VLM inference

## Backend Setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r vlm_requirements.txt
$env:FACE_AUTH_AES_KEY = "0000000000000000000000000000000000000000000000000000000000000000"
$env:PYTHONPATH = "."
$env:VLM_MODEL = "auto"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```powershell
curl.exe http://localhost:8000/health
```

Check VLM readiness:

```powershell
curl.exe http://localhost:8000/api/v1/vlm/status
```

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Docker Setup

The repository now includes:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`

Run both services:

```powershell
docker compose up --build
```

Stop:

```powershell
docker compose down
```

Logs:

```powershell
docker compose logs backend
docker compose logs frontend
```

## Local Pages To Test

| Page | Purpose |
| --- | --- |
| `http://localhost:5173/register` | Traditional registration |
| `http://localhost:5173/login` | Traditional video login |
| `http://localhost:5173/vlm-register` | VLM registration |
| `http://localhost:5173/vlm-login` | Hybrid VLM authentication |
| `http://localhost:5173/vlm-pure` | Pure VLM authentication |

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `FACE_AUTH_AES_KEY` | 64 zero characters | AES-256-GCM key |
| `JWT_PRIVATE_KEY` | `backend/keys/private.pem` | private key path |
| `JWT_PUBLIC_KEY` | `backend/keys/public.pem` | public key path |
| `VLM_MODEL` | `auto` | VLM model override |
| `VLM_MAX_RAM_GB` | `5.0` | soft VLM RAM target |
| `PYTHONPATH` | not set | backend module root |
| `VITE_API_PROXY_TARGET` | `http://localhost:8000` | frontend proxy target |

Supported `VLM_MODEL` values:

- `auto`
- `qwen`
- `moondream`
- `smolvlm`
- `disabled`

## Important Paths

| Path | Purpose |
| --- | --- |
| `backend/data/auth.db` | traditional auth database |
| `backend/data/vlm_ref_frames/` | stored VLM reference frames |
| `backend/weights/` | ONNX weights and optional VLM cache |
| `backend/weights/vlm_cache/` | downloaded VLM models |
| `backend/keys/` | JWT key files |

## Recommended Smoke Test

1. Start the backend.
2. Confirm `/health`.
3. Start the frontend.
4. Register a user at `/register`.
5. Authenticate the user at `/login`.
6. Register a VLM user at `/vlm-register`.
7. Authenticate the user at `/vlm-login`.
8. Authenticate the same user at `/vlm-pure`.
9. Confirm `/api/v1/vlm/status`.

## Operational Notes

- The first run may download YuNet, ArcFace, or VLM weights.
- VLM can be much slower than the traditional pipeline on CPU.
- Browser camera APIs require user permission.
- Upload-based routes do not perform live hardware anti-injection checks.
- Rate limiting is currently `5/minute` on sensitive endpoints.
- The stricter VLM prompt now denies access when phones, screens, replay media, printed images, or frozen-eye spoof patterns are visible.
