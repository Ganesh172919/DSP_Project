# DeepShield Guardian

DeepShield Guardian is a full-stack, deepfake-resistant face authentication platform built for data security and privacy coursework, capstone demos, and security-oriented prototyping. It combines:

- A React + TypeScript frontend with webcam capture, MediaPipe face/hand landmarks, guided enrollment, and live challenge-response UX
- A FastAPI backend with encrypted biometric templates, audit logs, challenge orchestration, and decision scoring
- Dedicated ML microservice stubs for face feature extraction and risk analysis
- PostgreSQL, Redis, Docker Compose, and Kubernetes starter manifests
- Documentation for architecture, security, deployment, user flows, and a thesis-style project report

## Repository Layout

- `apps/web`: frontend application
- `services/api`: FastAPI gateway and business logic
- `services/ml-face`: face analysis microservice
- `services/ml-risk`: risk-scoring microservice
- `docs`: architecture, report, API, security, deployment, and user guides
- `infra`: Nginx reverse proxy and Kubernetes starter manifests

## What Is Implemented

- Multi-step face enrollment flow with guided capture states
- Browser-side face and hand landmark extraction using MediaPipe Tasks
- Registration session handling and encrypted template storage
- Authentication attempt lifecycle with randomized challenge selection
- Baseline passive PAD scoring using image sharpness, exposure, spectral, and moire-like heuristics
- Baseline geometric recognition using deterministic landmark embeddings
- Liveness scoring for several live challenges such as blinking, smiling, mouth opening, nodding, shaking, brow raise, squinting, and distance change
- Decision engine with stage thresholds and weighted aggregate scoring
- Admin metrics and user profile APIs

## Important Scope Note

This repository is a production-oriented scaffold with working baseline heuristics. It is not a claim of certified ISO/NIST biometric performance. To reach enterprise deployment quality, you would still need:

- Calibrated face recognition models such as ArcFace/FaceNet
- PAD/deepfake models trained on curated attack datasets
- Formal bias testing, benchmark reporting, and threshold calibration
- Hardware-backed secret management and hardened production operations

## Quick Start

### Fastest Local Run On This Machine

Use the PowerShell helpers from the repo root:

```powershell
.\scripts\start-local.ps1
```

To stop everything:

```powershell
.\scripts\stop-local.ps1
```

To see which services are still running:

```powershell
.\scripts\status-local.ps1
```

### Option 1: Docker Compose

```bash
docker compose up --build
```

Frontend: `http://localhost`

API docs: `http://localhost/api/v1/health`

### Option 2: Local Development

Frontend:

```bash
cd apps/web
npm install
npm run dev
```

Backend:

```bash
cd services/api
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

Optional ML microservices:

```bash
cd services/ml-face
..\api\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8001

cd services/ml-risk
..\api\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8002
```

## Verification

- Python modules can be syntax-checked with `python -m compileall services/api/app services/ml-face/app services/ml-risk/app`
- Backend tests live in `services/api/tests`
- Frontend build validation uses `npm run build` inside `apps/web`
- Local startup helpers live in [start-local.ps1](C:/Users/RAVIPRAKASH/DSP_Project/scripts/start-local.ps1), [stop-local.ps1](C:/Users/RAVIPRAKASH/DSP_Project/scripts/stop-local.ps1), and [status-local.ps1](C:/Users/RAVIPRAKASH/DSP_Project/scripts/status-local.ps1)

## Documentation

- `docs/ai-models.md` - primary AI and authentication improvement guide
- `docs/ai-model-catalog.md`
- `docs/ai-model-appendix.md`
- `docs/architecture.md`
- `docs/report.md`
- `docs/api.md`
- `docs/security.md`
- `docs/user-manual.md`
- `docs/deployment.md`
