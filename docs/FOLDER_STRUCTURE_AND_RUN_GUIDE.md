# Folder Structure And Run Guide

Repository: [Ganesh172919/DSP_Project](https://github.com/Ganesh172919/DSP_Project)

This document explains:

- what should exist in the project folder
- which files are important
- how to run the project locally
- how to run the project with Docker
- what gets created automatically at runtime

## Recommended Top-Level Folder Layout

```text
DSP Project/
|-- backend/
|-- frontend/
|-- docs/
|-- docker-compose.yml
|-- README.md
|-- walkthrough.md
|-- analysis_and_approaches.md
`-- vlm_approaches.md
```

## Backend Folder Contents

```text
backend/
|-- app/
|   |-- main.py
|   |-- pipeline.py
|   |-- vlm_config.py
|   |-- vlm_pipeline.py
|   |-- vlm_routes.py
|   |-- config.py
|   |-- crypto.py
|   |-- video_utils.py
|   |-- instructions.py
|   |-- db/
|   `-- models/
|-- data/
|-- keys/
|-- training/
|-- weights/
|-- requirements.txt
|-- vlm_requirements.txt
|-- Dockerfile
`-- .dockerignore
```

### Important backend folders

- `app/`: all backend source code
- `app/models/`: detector, recognizer, liveness, deepfake, VLM reasoner
- `app/db/`: SQLAlchemy models and CRUD logic
- `data/`: runtime databases and stored VLM frames
- `weights/`: ONNX weights and optional VLM model cache
- `keys/`: JWT keys
- `training/`: optional training and evaluation scripts

### Important backend files

- `requirements.txt`: normal backend dependencies
- `vlm_requirements.txt`: VLM dependencies
- `Dockerfile`: backend container build file
- `app/vlm_config.py`: VLM thresholds, prompt text, and model selection

## Frontend Folder Contents

```text
frontend/
|-- src/
|   |-- api/
|   |-- components/
|   |-- pages/
|   `-- utils/
|-- index.html
|-- package.json
|-- package-lock.json
|-- vite.config.js
|-- Dockerfile
`-- .dockerignore
```

### Important frontend pages

- `src/pages/Register.jsx`
- `src/pages/Login.jsx`
- `src/pages/VLMRegister.jsx`
- `src/pages/VLMLogin.jsx`
- `src/pages/PureVLMLogin.jsx`

## Files And Folders Created Automatically

The project can create these automatically if they do not already exist:

- `backend/data/auth.db`
- `backend/data/vlm_ref_frames/`
- `backend/keys/private.pem`
- `backend/keys/public.pem`
- `backend/weights/face_detection_yunet_2023mar.onnx`
- `backend/weights/w600k_r50.onnx`
- `backend/weights/vlm_cache/`

## What You Should Keep In The Folder

For a working project checkout, make sure these exist:

- `backend/app`
- `backend/requirements.txt`
- `backend/vlm_requirements.txt`
- `frontend/src`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/vite.config.js`
- `docker-compose.yml`
- `README.md`

Optional but useful:

- `backend/weights/face_detection_yunet_2023mar.onnx`
- `backend/weights/w600k_r50.onnx`
- `docs/`

## Local Run Instructions

### Backend Setup

Use Python `3.11` or `3.12`.

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

### Frontend Setup

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

### Health Check

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

## Docker Run Instructions

This repository includes:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`

Run everything with:

```powershell
docker compose up --build
```

Services:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

Stop everything:

```powershell
docker compose down
```

View logs:

```powershell
docker compose logs backend
docker compose logs frontend
```

## VLM-Specific Usage Notes

The VLM prompt has been strengthened so both hybrid and pure VLM authentication deny access when:

- a mobile phone is shown to the camera
- a laptop screen or monitor is visible
- a replayed video is visible
- a printed image or paper face is visible
- a face appears inside another screen or rectangle
- the user's full face is not clearly visible
- eye state looks frozen across authentication frames

For best VLM results:

- keep only the real user's face in front of the camera
- keep the full face visible
- avoid showing any secondary device or photo
- blink naturally during the capture

## Main Test Pages

- `http://localhost:5173/register`
- `http://localhost:5173/login`
- `http://localhost:5173/vlm-register`
- `http://localhost:5173/vlm-login`
- `http://localhost:5173/vlm-pure`

## Main VLM Endpoints

- `POST /api/v1/vlm/register`
- `POST /api/v1/vlm/authenticate`
- `POST /api/v1/vlm/authenticate/pure`
- `GET /api/v1/vlm/status`
- `POST /api/v1/vlm/warmup`

## Troubleshooting

- If the backend starts slowly on first run, model downloads may be happening.
- If VLM is slow, CPU-only inference is probably being used.
- If the frontend cannot reach the backend in Docker, make sure `docker compose up --build` completed successfully and that both containers are running.
- If the browser camera does not start, allow camera permission for `localhost`.
- If authentication denies correctly when a phone or screen is visible, the stricter VLM prompt is working as intended.
