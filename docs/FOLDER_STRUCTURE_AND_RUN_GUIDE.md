# Folder Structure and Run Guide

Repository: [Ganesh172919/DSP_Project](https://github.com/Ganesh172919/DSP_Project)

If you want the full beginner walkthrough from GitHub ZIP download to running the project, use:

- [BEGINNER_GITHUB_ZIP_TO_RUN_GUIDE.md](BEGINNER_GITHUB_ZIP_TO_RUN_GUIDE.md)

This document focuses on the folder structure and the minimum files needed to run the project correctly.

## Required Top-Level Structure

```text
DSP Project/
|-- .env.example
|-- backend/
|-- frontend/
|-- docs/
|-- docker-compose.yml
|-- README.md
|-- walkthrough.md
|-- analysis_and_approaches.md
`-- vlm_approaches.md
```

## Required Backend Structure

```text
backend/
|-- app/
|   |-- config.py
|   |-- main.py
|   |-- pipeline.py
|   |-- vlm_config.py
|   |-- vlm_pipeline.py
|   |-- vlm_routes.py
|   |-- crypto.py
|   |-- video_utils.py
|   |-- db/
|   `-- models/
|-- data/
|-- keys/
|-- training/
|-- weights/
|-- requirements.txt
|-- vlm_requirements.txt
`-- Dockerfile
```

## Required Frontend Structure

```text
frontend/
|-- src/
|   |-- api/
|   |-- components/
|   |-- pages/
|   `-- utils/
|-- package.json
|-- package-lock.json
|-- vite.config.js
`-- Dockerfile
```

## Files Created Automatically

The project can create these automatically after setup or first run:

- `.env` after you copy it from `.env.example`
- `backend/data/auth.db`
- `backend/data/vlm_ref_frames/`
- `backend/keys/private.pem`
- `backend/keys/public.pem`
- `backend/weights/face_detection_yunet_2023mar.onnx`
- `backend/weights/w600k_r50.onnx`
- `backend/weights/vlm_cache/`
- `backend/venv/` if you use manual Python setup
- `frontend/node_modules/` if you use manual frontend setup

## `.env` Setup

Create the root `.env` file from the project root:

```powershell
Copy-Item .env.example .env
```

The backend now loads:

- the root `.env`
- `backend/.env` if you create one later

Docker Compose also uses the root `.env`.

## Manual Run Summary

Backend:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r vlm_requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

## Docker Run Summary

```powershell
Copy-Item .env.example .env
docker compose up --build
```

## Expected Final Structure After Setup

```text
DSP Project/
|-- .env
|-- .env.example
|-- backend/
|   |-- app/
|   |-- data/
|   |   |-- auth.db
|   |   `-- vlm_ref_frames/
|   |-- keys/
|   |   |-- private.pem
|   |   `-- public.pem
|   |-- venv/
|   |-- weights/
|   |   |-- face_detection_yunet_2023mar.onnx
|   |   |-- w600k_r50.onnx
|   |   `-- vlm_cache/
|   |-- requirements.txt
|   `-- vlm_requirements.txt
|-- frontend/
|   |-- node_modules/
|   |-- src/
|   |-- package.json
|   `-- vite.config.js
|-- docs/
|   `-- BEGINNER_GITHUB_ZIP_TO_RUN_GUIDE.md
|-- docker-compose.yml
`-- README.md
```

If your folder looks like this after setup, the project structure is ready for normal use.
