# Frontend And User Flows

The frontend is a React 18 application built with Vite. It uses browser camera APIs to capture frames or video and Axios to send multipart form data to the FastAPI backend.

## Frontend Stack

| Area | Tool |
| --- | --- |
| UI framework | React 18 |
| Build tool | Vite |
| Routing | React Router |
| HTTP client | Axios |
| Camera access | `navigator.mediaDevices.getUserMedia` |
| Video recording | `MediaRecorder` |

## Routes

| Browser route | Component | Backend path |
| --- | --- | --- |
| `/` | `Register` | `/api/v1/register` |
| `/register` | `Register` | `/api/v1/register` |
| `/login` | `Login` | `/api/v1/authenticate/video` |
| `/vlm-register` | `VLMRegister` | `/api/v1/vlm/register` |
| `/vlm-login` | `VLMLogin` | `/api/v1/vlm/authenticate` |

## Axios Configuration

`frontend/src/api/client.js` creates an Axios client:

```js
baseURL: '/api/v1'
timeout: 60000
```

Vite proxies `/api` requests to the backend during local development.

## Traditional Registration Flow

Component:

```text
frontend/src/pages/Register.jsx
```

Flow:

1. User enters name and email.
2. Browser asks for camera permission.
3. UI captures multiple still frames.
4. The page sends repeated `face_data` file fields to `/api/v1/register`.
5. The backend returns `user_id`, `username`, `liveness_score`, `face_quality`, and `status`.
6. The UI shows success or failure.

## Traditional Login Flow

Component:

```text
frontend/src/pages/Login.jsx
```

Flow:

1. User enters username.
2. Browser opens the camera.
3. UI records a 4-second WebM video.
4. The page sends `username` and `video` to `/api/v1/authenticate/video`.
5. The backend returns decision, confidence, scores, threat flags, processing time, and either a JWT or denial reason.
6. The UI displays Face Match, Liveness, and Deepfake score bars.

## VLM Registration Flow

Component:

```text
frontend/src/pages/VLMRegister.jsx
```

Flow:

1. User enters name and email.
2. Browser opens the camera.
3. UI runs a 3-second countdown.
4. UI records a 5-second WebM video.
5. The page sends `username`, `email`, and `video` to `/api/v1/vlm/register`.
6. Backend builds the normal biometric profile and selects VLM reference frames.
7. The UI shows face quality, liveness score, and number of VLM reference frames stored.

## VLM Login Flow

Component:

```text
frontend/src/pages/VLMLogin.jsx
```

Flow:

1. User enters username.
2. Browser opens the camera.
3. UI runs a 3-second countdown.
4. UI records a 5-second WebM video.
5. The page auto-submits the video to `/api/v1/vlm/authenticate`.
6. Backend runs traditional video authentication first.
7. If traditional auth grants, backend invokes the VLM when reference frames are available.
8. UI displays traditional scores, VLM scores, VLM model name, VLM override status, and natural-language VLM reasoning.

## User-Facing Score Meanings

| Score | Good direction | Meaning |
| --- | --- | --- |
| Face Match | Higher is better | ArcFace cosine similarity to stored template. |
| Liveness | Higher is better | Evidence that the face appears live and not a spoof. |
| Deepfake | Lower is better | Estimated synthetic or manipulation risk. |
| VLM Identity | Higher is better | VLM confidence that reference and auth frames show the same person. |
| VLM Liveness | Higher is better | VLM confidence that the auth frames show a live person. |
| VLM Authenticity | Higher is better | VLM confidence that the auth frames are not spoofed or manipulated. |

## Browser Requirements

- Camera permission must be granted.
- `MediaRecorder` must support WebM or a compatible recording type.
- Local development should use `localhost` or another secure context where camera APIs are allowed.

## UX Notes For Demonstration

- Register with good lighting and keep the face centered.
- For traditional registration, capture multiple clear still frames.
- For VLM registration, move the head slightly during the 5-second capture.
- For VLM login, use a user registered through VLM registration when full VLM analysis is required.
- If a user was registered through the traditional page, VLM login can still run the traditional pipeline, but it will report missing VLM reference frames.

## Current Frontend/Backend Alignment Note

The current frontend and backend disagree on VLM registration input:

- `VLMRegister.jsx` records a 5-second video and sends form field `video`.
- The current `backend/app/vlm_routes.py` route for `/api/v1/vlm/register` expects repeated image files under `face_data`.

The traditional register page and VLM authenticate page remain conceptually aligned with their documented backend routes. The VLM registration page needs one integration pass before a browser demo:

- either make the frontend capture/send repeated `face_data` frames
- or make the backend accept a `video` upload and use `VLMAuthPipeline.register_face_from_video()`
