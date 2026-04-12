# DSP Project: AI-Based Facial Authentication with Hybrid and Pure VLM Modes

GitHub repository: [Ganesh172919/DSP_Project](https://github.com/Ganesh172919/DSP_Project)

This project is a full-stack facial authentication system with:

- a React frontend
- a FastAPI backend
- traditional face verification
- liveness and deepfake checks
- hybrid VLM authentication
- pure VLM authentication

The VLM layer is now stricter for spoof detection. It is instructed to deny access when authentication frames show a mobile phone, tablet, laptop screen, monitor, TV, replayed video, printed photo, picture, poster, hard copy, or a face inside another screen/rectangle. It also checks whether the full real face is visible in the main frame and whether blink or eye-state changes are present across authentication frames.

## Start Here

If you downloaded this project as a ZIP from GitHub and want a beginner-friendly setup guide, read:

- [docs/BEGINNER_GITHUB_ZIP_TO_RUN_GUIDE.md](docs/BEGINNER_GITHUB_ZIP_TO_RUN_GUIDE.md)

Other helpful docs:

- [docs/FOLDER_STRUCTURE_AND_RUN_GUIDE.md](docs/FOLDER_STRUCTURE_AND_RUN_GUIDE.md)
- [docs/SETUP_AND_OPERATIONS.md](docs/SETUP_AND_OPERATIONS.md)
- [docs/VLM_HYBRID_AUTHENTICATION.md](docs/VLM_HYBRID_AUTHENTICATION.md)

## Authentication Modes

- `Register`: traditional registration
- `Login`: traditional video authentication
- `VLM Register`: stores registration reference frames for VLM use
- `Hybrid VLM Login`: traditional pipeline first, VLM reasoning second
- `Pure VLM Login`: VLM-only authentication

## Main Security Layers

- YuNet face detection and alignment
- ArcFace ONNX face embeddings
- liveness fusion
- deepfake defense
- AES-encrypted stored embeddings
- JWT generation
- VLM reasoning over registration and authentication frames

## Updated VLM Anti-Spoof Rules

Both hybrid and pure VLM modes now use stronger anti-spoof instructions:

- deny if a phone, tablet, laptop screen, monitor, TV, replayed video, printed photo, hard copy, or picture is visible
- deny if the face appears inside another screen, playback window, gallery image, or rectangle
- deny if the user is holding spoof media near the face
- deny unless the real user's full face is clearly visible in the main frame
- keep liveness low if eyes look frozen or identical across authentication frames
- compare registration reference frames against current authentication frames before deciding

Hybrid mode also has an extra safeguard: if the VLM returns explicit spoof red flags such as `visible_mobile_phone`, `printed_photo`, `replayed_video`, `face_inside_secondary_rectangle`, or `full_face_not_visible`, the hybrid route denies immediately instead of waiting only for the fused-score veto threshold.

## Recommended Top-Level Folder Structure

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

## Important Files and Folders

You should have these folders and files in the repo before running:

- `backend/app/`
- `backend/requirements.txt`
- `backend/vlm_requirements.txt`
- `backend/Dockerfile`
- `frontend/src/`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `docs/`

These are created automatically during setup or first run:

- `.env` after you copy it from `.env.example`
- `backend/data/auth.db`
- `backend/data/vlm_ref_frames/`
- `backend/keys/private.pem`
- `backend/keys/public.pem`
- `backend/weights/face_detection_yunet_2023mar.onnx`
- `backend/weights/w600k_r50.onnx`
- `backend/weights/vlm_cache/`
- `backend/venv/` after manual backend setup
- `frontend/node_modules/` after frontend install

## Quick Local Run

### 1. Create `.env`

From the project root:

```powershell
Copy-Item .env.example .env
```

### 2. Start the backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r vlm_requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Start the frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/health`

## Quick Docker Run

From the project root:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

Stop services:

```powershell
docker compose down
```

## VLM Model Loading Notes

On the first run, the project can download or create:

- YuNet face detector
- ArcFace ONNX recognition model
- VLM model cache in `backend/weights/vlm_cache/`
- SQLite database files
- JWT key files

VLM startup can be slow on CPU-only systems. This is expected.

## Main Frontend Pages

- `/register`
- `/login`
- `/vlm-register`
- `/vlm-login`
- `/vlm-pure`

## Main Backend Endpoints

- `GET /health`
- `POST /api/v1/register`
- `POST /api/v1/authenticate/video`
- `POST /api/v1/vlm/register`
- `POST /api/v1/vlm/authenticate`
- `POST /api/v1/vlm/authenticate/pure`
- `GET /api/v1/vlm/status`
- `POST /api/v1/vlm/warmup`

## Documentation Map

- [docs/BEGINNER_GITHUB_ZIP_TO_RUN_GUIDE.md](docs/BEGINNER_GITHUB_ZIP_TO_RUN_GUIDE.md): beginner setup from ZIP download to running the full project
- [docs/FOLDER_STRUCTURE_AND_RUN_GUIDE.md](docs/FOLDER_STRUCTURE_AND_RUN_GUIDE.md): required folders/files and expected runtime structure
- [docs/SETUP_AND_OPERATIONS.md](docs/SETUP_AND_OPERATIONS.md): local and Docker setup reference
- [docs/VLM_HYBRID_AUTHENTICATION.md](docs/VLM_HYBRID_AUTHENTICATION.md): hybrid and pure VLM architecture, prompts, and decision flow

## Important Notes

- For the easiest setup, use Python `3.11` or `3.12`.
- Docker is optional. Manual setup also works.
- Allow camera permission in the browser.
- For best VLM results, keep only the real user's full face in the frame.
- Do not show a phone, tablet, laptop, printed image, replay screen, or another displayed face during authentication.
