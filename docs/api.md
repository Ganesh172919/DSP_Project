# API Guide

FastAPI generates interactive OpenAPI docs automatically after the backend starts.

## Base URL

`/api/v1`

## Endpoints

### `POST /registration/start`

Creates or refreshes a user enrollment session.

Request body:

```json
{
  "full_name": "Ada Lovelace",
  "email": "ada@example.com",
  "password": "strongpassword123",
  "accessibility_profile": {
    "eye_only": false,
    "no_head_turns": false
  }
}
```

### `POST /registration/{session_id}/frame`

Sends one enrollment capture with landmarks, optional frame image, and client metrics.

### `POST /registration/{session_id}/complete`

Builds the encrypted biometric template and stores its quality/security scores.

### `POST /authentication/start`

Begins an authentication attempt and returns a randomized challenge sequence.

### `POST /authentication/{attempt_id}/frame`

Appends one live observation during the authentication attempt.

### `POST /authentication/{attempt_id}/complete`

Evaluates the full challenge sequence and returns the final decision.

### `GET /admin/metrics`

Returns dashboard counters and recent audit events.

### `GET /users/profile?email={email}`

Returns profile status and recent authentication history.

## Error Handling

- `400`: invalid flow state or insufficient data
- `404`: unknown user, session, or attempt
- `410`: expired enrollment session
- `422`: schema validation error

## Security Notes

- Biometric templates are encrypted before they are stored
- The API is designed to remain authoritative even when the browser performs landmark extraction
- For production deployment, add JWT session issuance, rate limiting, CSRF protections for cookie-based sessions, and HSTS/CSP headers at the reverse proxy

