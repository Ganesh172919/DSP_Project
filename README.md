# DSP Project: AI-Based Facial Authentication with Hybrid And Pure VLM Modes

GitHub repository: [Ganesh172919/DSP_Project](https://github.com/Ganesh172919/DSP_Project)

This project is a full-stack facial authentication system built with a React frontend and a FastAPI backend. It combines traditional face verification, liveness checks, deepfake defense, and Vision Language Model reasoning for stronger spoof detection.

The latest update strengthens both `Hybrid VLM Authenticate` and `Pure VLM Authenticate` by tightening the prompt sent to the VLM. The model is now instructed to deny access when it sees a mobile phone, tablet, laptop screen, monitor, replayed video, printed photo, picture, poster, or any face shown inside another screen or rectangle. It is also instructed to require a clearly visible full face in the main camera frame and to check for blink evidence across frames.

## Implemented Authentication Modes

- Traditional registration: `Register`
- Traditional video login: `Login`
- VLM registration with stored reference frames: `VLM Register`
- Hybrid VLM login: traditional pipeline first, VLM judge second
- Pure VLM login: VLM-only identity, liveness, and authenticity judgment

## Main Security Layers

- YuNet face detection and alignment
- ArcFace ONNX face embeddings
- Liveness fusion with CNN, texture, moire, motion, micro-movement, and rPPG
- Deepfake scoring with spectral, CNN, boundary, reflection, skin, color, and temporal signals
- AES-256-GCM encrypted face embeddings
- JWT generation with RS256
- VLM reasoning over registration and authentication frames

## Strict VLM Anti-Spoof Policy

The shared VLM prompt now tells the model to:

- Deny if any mobile phone, tablet, laptop, monitor, TV, printed photo, paper, picture, poster, or replayed video is visible.
- Deny if the face is shown inside another screen, playback window, bezel, or secondary rectangle.
- Deny unless the live user's full face is clearly visible in the main frame.
- Treat frozen eye state across authentication frames as negative liveness evidence.
- Keep the overall score near zero when device-based or replay-based spoofing is detected.

These prompt rules are applied to both:

- `/api/v1/vlm/authenticate`
- `/api/v1/vlm/authenticate/pure`

## Repository Structure

```text
DSP Project/
|-- backend/
|   |-- app/
|   |   |-- main.py
|   |   |-- pipeline.py
|   |   |-- vlm_config.py
|   |   |-- vlm_pipeline.py
|   |   |-- vlm_routes.py
|   |   |-- config.py
|   |   |-- crypto.py
|   |   |-- video_utils.py
|   |   |-- instructions.py
|   |   |-- db/
|   |   `-- models/
|   |-- data/
|   |-- keys/
|   |-- training/
|   |-- weights/
|   |-- requirements.txt
|   |-- vlm_requirements.txt
|   |-- Dockerfile
|   `-- .dockerignore
|-- frontend/
|   |-- src/
|   |   |-- api/
|   |   |-- components/
|   |   |-- pages/
|   |   `-- utils/
|   |-- index.html
|   |-- package.json
|   |-- package-lock.json
|   |-- vite.config.js
|   |-- Dockerfile
|   `-- .dockerignore
|-- docs/
|   |-- FOLDER_STRUCTURE_AND_RUN_GUIDE.md
|   |-- SETUP_AND_OPERATIONS.md
|   |-- VLM_HYBRID_AUTHENTICATION.md
|   `-- ...
|-- docker-compose.yml
|-- analysis_and_approaches.md
|-- vlm_approaches.md
|-- walkthrough.md
`-- README.md
```

## What Should Be Present In The Folder

For a clean clone, these are the important folders and files:

- `backend/app/` for all FastAPI and model code
- `backend/requirements.txt` for the traditional backend dependencies
- `backend/vlm_requirements.txt` for VLM dependencies
- `backend/weights/` for ONNX weights and optional downloaded VLM cache
- `backend/data/` for SQLite databases and stored VLM reference frames
- `backend/keys/` for JWT keys
- `frontend/src/` for the React app
- `frontend/package.json` and `frontend/package-lock.json` for frontend dependencies
- `docker-compose.yml` for full-project Docker startup

Important notes:

- `backend/weights/face_detection_yunet_2023mar.onnx` and `backend/weights/w600k_r50.onnx` can already be present, or the backend can download them automatically if they are missing.
- `backend/weights/vlm_cache/` is created after the first VLM model download.
- `backend/data/auth.db` and `backend/data/faceauth.db` are runtime databases.
- `backend/data/vlm_ref_frames/` is created after VLM registrations.
- `backend/keys/private.pem` and `backend/keys/public.pem` are created automatically if needed.

## How To Run The Project Locally

### 1. Backend

Use Python `3.11` or `3.12` for the easiest setup.

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

Expected response:

```json
{
  "status": "ok",
  "pipeline_loaded": true
}
```

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

The frontend proxy sends `/api` requests to `http://localhost:8000`.

## How To Run The Project With Docker

The repository now includes:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`

Start the full stack:

```powershell
docker compose up --build
```

After startup:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Health: `http://localhost:8000/health`

Useful Docker commands:

```powershell
docker compose up --build
docker compose down
docker compose logs backend
docker compose logs frontend
```

The Docker setup mounts these folders for persistence:

- `backend/data`
- `backend/weights`
- `backend/keys`

## Frontend Pages

| Route | Purpose |
| --- | --- |
| `/register` | Traditional registration with 5 captured face images |
| `/login` | Traditional video authentication |
| `/vlm-register` | VLM registration with stored reference images |
| `/vlm-login` | Hybrid VLM authentication |
| `/vlm-pure` | Pure VLM authentication |

## Main Backend Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend health check |
| `POST` | `/api/v1/register` | Traditional registration |
| `POST` | `/api/v1/authenticate/video` | Traditional video authentication |
| `GET` | `/api/v1/challenge` | Challenge generation |
| `POST` | `/api/v1/authenticate/challenge` | Challenge-based authentication |
| `POST` | `/api/v1/vlm/register` | VLM registration with repeated `face_data` images |
| `POST` | `/api/v1/vlm/authenticate` | Hybrid VLM authentication |
| `POST` | `/api/v1/vlm/authenticate/pure` | Pure VLM authentication |
| `GET` | `/api/v1/vlm/status` | VLM hardware and readiness status |
| `POST` | `/api/v1/vlm/warmup` | Preload the VLM |

## Core Runtime Flow

### Traditional Flow

```text
Captured frames or video
  -> YuNet face detection
  -> face alignment
  -> ArcFace identity match
  -> liveness fusion
  -> deepfake checks
  -> grant or deny
```

### Hybrid VLM Flow

```text
Traditional GRANT
  -> load VLM registration frames
  -> extract VLM auth frames
  -> run VLM reasoning
  -> fuse traditional score and VLM score
  -> optional VLM veto
```

### Pure VLM Flow

```text
VLM reference frames
  -> extract auth frames
  -> send reg + auth frames to VLM
  -> VLM decides same person, live, authentic, overall
  -> grant or deny
```

## Documentation Map

- `README.md`: main project entry point
- `docs/FOLDER_STRUCTURE_AND_RUN_GUIDE.md`: exact folder layout, required files, local run, Docker run, and troubleshooting
- `docs/SETUP_AND_OPERATIONS.md`: setup and operational reference
- `docs/VLM_HYBRID_AUTHENTICATION.md`: hybrid and pure VLM design, prompts, and fusion
- `docs/API_REFERENCE.md`: endpoint reference
- `docs/DATABASE_AND_STORAGE.md`: storage and database behavior
- `walkthrough.md`: practical project walkthrough
- `analysis_and_approaches.md`: design analysis and implementation notes

## Important Notes

- The first run can download models and may take time.
- VLM inference is slower than the traditional pipeline, especially on CPU.
- Localhost camera permission is required in the browser.
- The VLM prompt is now stricter, but this is still a research/demo project and not a production-certified biometric system.
- For best VLM results, keep the user's full face centered and do not place any phone, laptop, tablet, printed image, or replay screen in front of the camera.
