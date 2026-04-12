# Beginner Guide: From GitHub ZIP Download to Running the Full Project

Repository: [Ganesh172919/DSP_Project](https://github.com/Ganesh172919/DSP_Project)

This guide is written for beginners. If you follow these steps in order, you should be able to run the full project either:

- manually, with separate backend and frontend terminals
- with Docker, using one command

## 1. What You Need Before Starting

Install these first:

- Python `3.11` or `3.12`
- Node.js `20` or later
- npm
- Docker Desktop only if you want the Docker method

Recommended for Windows users:

- use PowerShell
- allow camera access in your browser
- keep at least several GB of free disk space for models and dependencies

## 2. Download the Project ZIP from GitHub

1. Open the repository: [Ganesh172919/DSP_Project](https://github.com/Ganesh172919/DSP_Project)
2. Click `Code`
3. Click `Download ZIP`
4. Wait for the ZIP file to finish downloading

## 3. Extract the ZIP File

1. Go to your Downloads folder
2. Right-click the ZIP file
3. Click `Extract All...`
4. Extract it to a folder you can easily open, for example:

```text
C:\Users\YourName\Downloads\DSP Project
```

If GitHub gives the extracted folder a name like `DSP_Project-main`, that is fine. You can keep that name or rename it to `DSP Project`.

## 4. Open the Project Folder

Open PowerShell inside the extracted project folder.

Example:

```powershell
cd "C:\Users\YourName\Downloads\DSP Project"
```

## 5. Check the Folder Structure Before Running

Before you do anything else, the extracted project folder should contain at least this:

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

If `backend`, `frontend`, `docs`, `docker-compose.yml`, and `README.md` are present, you can continue.

## 6. Create the `.env` File

This project now supports a root `.env` file. It is used for manual backend runs and for Docker Compose.

From the project root, run:

```powershell
Copy-Item .env.example .env
```

This creates:

```text
DSP Project/.env
```

You can open it with Notepad:

```powershell
notepad .env
```

The default `.env` file is enough for local testing.

Current example values:

```env
FACE_AUTH_AES_KEY=0000000000000000000000000000000000000000000000000000000000000000
VLM_MODEL=auto
VLM_MAX_RAM_GB=5.0
MOONDREAM_REVISION=2025-06-21
VITE_API_PROXY_TARGET=http://backend:8000
```

Notes:

- `FACE_AUTH_AES_KEY` is a demo key for local development only.
- `VLM_MODEL=auto` lets the backend choose the best VLM based on your hardware.
- `VITE_API_PROXY_TARGET` is mainly used by Docker.

## 7. Manual Method: Run Without Docker

Use this method if you want to run the backend and frontend yourself in separate terminals.

## 7A. Backend Setup

Open the first PowerShell window and run:

```powershell
cd "C:\Users\YourName\Downloads\DSP Project\backend"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r vlm_requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

What this does:

- creates a Python virtual environment
- activates it
- installs backend packages
- installs VLM packages
- starts the FastAPI backend on port `8000`

If the backend starts correctly, you should be able to open:

- `http://localhost:8000/health`

## 7B. What Happens on First Backend Run

On the first run, the backend may create or download these items automatically:

- `backend/data/auth.db`
- `backend/data/vlm_ref_frames/`
- `backend/keys/private.pem`
- `backend/keys/public.pem`
- `backend/weights/face_detection_yunet_2023mar.onnx`
- `backend/weights/w600k_r50.onnx`

If you use VLM endpoints, the backend may also download VLM model files into:

```text
backend/weights/vlm_cache/
```

This first run can take time. That is normal.

## 7C. Optional: Warm Up the VLM Model

After the backend starts, you can warm up the VLM model by opening:

```text
http://localhost:8000/api/v1/vlm/status
```

or by calling:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/vlm/warmup
```

This can trigger the first VLM load/download before the first authentication attempt.

## 7D. Frontend Setup

Open a second PowerShell window and run:

```powershell
cd "C:\Users\YourName\Downloads\DSP Project\frontend"
npm install
npm run dev
```

What this does:

- installs frontend dependencies
- starts the React/Vite frontend on port `5173`

Open:

- `http://localhost:5173`

## 7E. Pages You Can Test

Open these pages in the browser:

- `http://localhost:5173/register`
- `http://localhost:5173/login`
- `http://localhost:5173/vlm-register`
- `http://localhost:5173/vlm-login`
- `http://localhost:5173/vlm-pure`

## 8. Docker Method: Run the Full Project with One Command

Use this method if you want Docker to run the backend and frontend for you.

## 8A. Install and Start Docker Desktop

1. Install Docker Desktop
2. Open Docker Desktop
3. Wait until Docker shows that it is running

## 8B. Make Sure `.env` Exists

From the project root:

```powershell
Copy-Item .env.example .env
```

You only need to do this once.

## 8C. Start the Full Stack

From the project root, run:

```powershell
docker compose up --build
```

What this does:

- builds the backend image
- builds the frontend image
- starts both containers
- uses your root `.env` values for the container environment

Open:

- frontend: `http://localhost:5173`
- backend: `http://localhost:8000`
- health check: `http://localhost:8000/health`

## 8D. Stop Docker Services

When you are done, stop the containers with:

```powershell
docker compose down
```

## 8E. View Docker Logs

If something is not working, check logs:

```powershell
docker compose logs backend
docker compose logs frontend
```

## 9. What Models and Files Load During Setup

Traditional pipeline files:

- YuNet face detector
- ArcFace recognition model
- SQLite database files
- JWT key files

VLM files:

- SmolVLM, moondream2, or Qwen cache depending on available hardware and your `VLM_MODEL` setting

Where VLM models are stored:

```text
backend/weights/vlm_cache/
```

Important note:

- On low-RAM systems, the backend may auto-select `SmolVLM-256M-Instruct`
- On stronger systems, it may use `moondream2` or `Qwen2.5-VL`
- VLM loading is usually much slower than the traditional pipeline

## 10. How the New VLM Protection Works

The VLM prompt is now stricter in both hybrid and pure modes.

It is instructed to deny access if authentication frames show:

- a mobile phone or tablet
- a laptop screen, monitor, or TV
- a replayed video or recorded clip
- a printed photo or hard copy
- a picture, poster, or displayed face
- a face inside another screen, gallery image, playback window, or rectangle
- a face blocked by a device
- a full face that is not clearly visible
- frozen eye states with weak blink evidence

Hybrid mode now has one more safeguard:

- if the VLM returns explicit spoof red flags such as `visible_mobile_phone`, `printed_photo`, `replayed_video`, or `full_face_not_visible`, the hybrid route denies immediately

## 11. Final Folder Structure After Successful Setup

After you finish setup and run the project at least once, the important structure should look like this:

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
|   |-- training/
|   |-- venv/                     # manual setup only
|   |-- weights/
|   |   |-- face_detection_yunet_2023mar.onnx
|   |   |-- w600k_r50.onnx
|   |   `-- vlm_cache/
|   |-- requirements.txt
|   |-- vlm_requirements.txt
|   `-- Dockerfile
|-- frontend/
|   |-- node_modules/             # manual setup only
|   |-- src/
|   |-- package.json
|   |-- package-lock.json
|   |-- vite.config.js
|   `-- Dockerfile
|-- docs/
|   |-- BEGINNER_GITHUB_ZIP_TO_RUN_GUIDE.md
|   |-- FOLDER_STRUCTURE_AND_RUN_GUIDE.md
|   |-- SETUP_AND_OPERATIONS.md
|   `-- VLM_HYBRID_AUTHENTICATION.md
|-- docker-compose.yml
`-- README.md
```

If your folder looks like this, then the project has the structure needed to run correctly.

## 12. Beginner Troubleshooting

- If `python` is not recognized, install Python and reopen PowerShell.
- If `npm` is not recognized, install Node.js and reopen PowerShell.
- If `docker compose` is not recognized, install Docker Desktop and make sure it is running.
- If the backend is slow on the first VLM request, model download/loading is probably happening.
- If the browser camera does not work, allow camera permission for `localhost`.
- If VLM denies access when a phone or printed photo is visible, that means the stricter anti-spoof rules are working.

## 13. Recommended First Test

1. Create `.env`
2. Start the backend
3. Open `http://localhost:8000/health`
4. Start the frontend
5. Open `http://localhost:5173`
6. Register one user
7. Test standard login
8. Register VLM reference frames
9. Test hybrid VLM login
10. Test pure VLM login

That is the safest beginner path to confirm the whole project is working.
