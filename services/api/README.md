# DeepShield Guardian API

FastAPI gateway for registration, authentication, admin metrics, and encrypted biometric template handling.

## Run

```bash
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

## Key Endpoints

- `POST /api/v1/registration/start`
- `POST /api/v1/registration/{session_id}/frame`
- `POST /api/v1/registration/{session_id}/complete`
- `POST /api/v1/authentication/start`
- `POST /api/v1/authentication/{attempt_id}/frame`
- `POST /api/v1/authentication/{attempt_id}/complete`
- `GET /api/v1/admin/metrics`
- `GET /api/v1/users/profile`
