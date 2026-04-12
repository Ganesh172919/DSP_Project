# Setup and Operations

Repository: [Ganesh172919/DSP_Project](https://github.com/Ganesh172919/DSP_Project)

For the full beginner walkthrough, use:

- [BEGINNER_GITHUB_ZIP_TO_RUN_GUIDE.md](BEGINNER_GITHUB_ZIP_TO_RUN_GUIDE.md)

For the exact folder layout, use:

- [FOLDER_STRUCTURE_AND_RUN_GUIDE.md](FOLDER_STRUCTURE_AND_RUN_GUIDE.md)

This document is the shorter operational reference.

## Prerequisites

- Python `3.11` or `3.12`
- Node.js `20+`
- npm
- Docker Desktop if you want containerized setup
- browser camera access

## `.env` Setup

Create the root `.env` file from the project root:

```powershell
Copy-Item .env.example .env
```

Important environment variables:

- `FACE_AUTH_AES_KEY`
- `VLM_MODEL`
- `VLM_MAX_RAM_GB`
- `MOONDREAM_REVISION`
- `VITE_API_PROXY_TARGET`

Supported `VLM_MODEL` values:

- `auto`
- `qwen`
- `moondream`
- `smolvlm`
- `disabled`

## Manual Backend Setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r vlm_requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Useful checks:

```powershell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/api/v1/vlm/status
curl.exe -X POST http://localhost:8000/api/v1/vlm/warmup
```

## Manual Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

Frontend URL:

- `http://localhost:5173`

## Docker Setup

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Useful Docker commands:

```powershell
docker compose down
docker compose logs backend
docker compose logs frontend
```

## Key Runtime Paths

- `backend/data/auth.db`
- `backend/data/vlm_ref_frames/`
- `backend/weights/`
- `backend/weights/vlm_cache/`
- `backend/keys/`

## Main Pages

- `http://localhost:5173/register`
- `http://localhost:5173/login`
- `http://localhost:5173/vlm-register`
- `http://localhost:5173/vlm-login`
- `http://localhost:5173/vlm-pure`

## Main Endpoints

- `GET /health`
- `POST /api/v1/register`
- `POST /api/v1/authenticate/video`
- `POST /api/v1/vlm/register`
- `POST /api/v1/vlm/authenticate`
- `POST /api/v1/vlm/authenticate/pure`
- `GET /api/v1/vlm/status`
- `POST /api/v1/vlm/warmup`

## Operational Notes

- The first run may download YuNet, ArcFace, and VLM model files.
- CPU-only VLM inference is slower than the traditional pipeline.
- The stricter VLM prompt denies device, screen, replay, printed-photo, and full-face-visibility attacks more aggressively.
- The hybrid route now force-denies when explicit spoof red flags are returned by the VLM.
