# User Manual

## Prerequisites

- A laptop or desktop with a functioning webcam
- Node.js 22 or Docker
- Python 3.11 for the backend runtime
- Stable front lighting and a neutral background

## Installation

### Docker

```bash
docker compose up --build
```

### Manual

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

## Registration Walkthrough

1. Open `/register`.
2. Enter your name, email, and password.
3. Click `Start Enrollment`.
4. Follow each capture step in order:
   - front
   - left
   - right
   - up
   - down
   - smile
   - frown
   - brow raise
   - squint
   - mouth open
5. Click `Finalize Registration`.

## Authentication Walkthrough

1. Open `/authenticate`.
2. Enter the email used during registration.
3. Click `Start Authentication`.
4. Click `Begin Live Scan`.
5. Perform each on-screen challenge before the timer window expires.
6. Review the final result and per-stage scores.

## Troubleshooting

- If the face guide never stabilizes, increase front lighting and move closer.
- If capture quality remains low, clean the webcam and wait for autofocus.
- If authentication fails after appearance changes, repeat registration.
- If camera access fails, verify browser permission settings and close any virtual-camera software.

