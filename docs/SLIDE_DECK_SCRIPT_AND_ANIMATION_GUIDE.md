# Slide Deck Script And Animation Guide

This document is a presentation guide for the interactive deck in:

```text
docs/interactive_auth_presentation/
```

It explains what each slide is meant to communicate, what animation or motion is used, and how to speak through the facial authentication process clearly.

## Presenter Goal

The goal is to explain the system as a layered security pipeline, not as a single face-recognition model. The audience should understand that the project asks several separate questions:

1. Is there a usable face?
2. Is this the registered identity?
3. Does the input appear live?
4. Does it look synthetic or manipulated?
5. Can the user respond to a fresh challenge?
6. Can the optional VLM reason about visual consistency?
7. Was the final decision logged and returned securely?

## Slide 1: Opening

### Title

AI-Based Facial Authentication With Liveness, Deepfake Defense, And VLM Reasoning

### Visual Motion

- Phone-like frame scans the face.
- Five landmark points pulse.
- Model names move as a stack.

### What To Say

"This project is a secure facial authentication system. It does not only compare two face images. It checks face quality, identity, liveness, spoofing risk, deepfake risk, optional challenge compliance, and optional VLM reasoning."

### Key Message

The system is layered. A successful login needs agreement from multiple signals.

### Technical Points

- React captures frames or video.
- FastAPI receives multipart uploads.
- YuNet detects and aligns the face.
- ArcFace verifies identity.
- Liveness and deepfake modules check trustworthiness.
- VLM can add natural-language reasoning.

### Transition

"Now let us follow one capture from the browser all the way to the final decision."

## Slide 2: Complete System Flow

### Visual Motion

- Pipeline nodes activate one by one.
- The active block moves from capture to response.

### What To Say

"The flow starts in the browser camera. The frontend sends multipart data to FastAPI. The backend decodes media, runs model layers, applies thresholds, logs the attempt, and returns a JSON decision."

### Key Message

Every step has a purpose. The system is not a black box.

### Step Explanation

| Step | Explanation |
| --- | --- |
| Capture | Browser obtains camera data. |
| Upload | Axios sends form data. |
| FastAPI | Route validates request and loads user. |
| YuNet | Face is detected and aligned. |
| ArcFace | Identity embedding is compared. |
| Liveness | Real-person evidence is fused. |
| Deepfake | Synthetic-media probability is estimated. |
| Decision | Threshold gates grant or deny. |
| Storage | Templates and logs are persisted. |
| Response | UI displays scores and result. |

### Transition

"Before authentication can happen, the system needs a registered biometric template."

## Slide 3: Registration

### Visual Motion

- Five face frames pulse.
- Embedding bars rise.
- Template pill appears as encrypted.

### What To Say

"Registration captures multiple frames. Each accepted face is detected, aligned, passed through ArcFace, and converted into an embedding. The embeddings are averaged and normalized to make one stable identity template."

### Key Message

Multiple registration samples make the stored template more robust than a single image.

### Technical Details

- The frontend sends repeated `face_data` files.
- The backend decodes JPEG bytes with OpenCV.
- YuNet rejects low-quality frames.
- ArcFace generates 512-dimensional vectors.
- The averaged template is L2-normalized.
- AES-256-GCM encrypts the template before SQLite storage.

### Mention Carefully

If presenting VLM registration, note the current integration warning:

- the working-tree backend route expects `face_data`
- the current VLM registration page sends `video`
- align that contract before a live browser demo

### Transition

"Once the user is registered, each model has a specific job during login."

## Slide 4: Model Roles

### Visual Motion

- Model cards respond on hover.
- Each card has a layer label.

### What To Say

"Each model is a specialist. YuNet does not decide identity. ArcFace does not prove liveness. The deepfake detector does not replace identity matching. The strength comes from combining them."

### Model Explanation

| Model | Simple explanation |
| --- | --- |
| Anti-Injection | Checks whether a live camera source appears physical. |
| YuNet | Finds the face and landmarks. |
| ArcFace | Converts the face into an identity vector. |
| Liveness Fusion | Checks live-person evidence. |
| Deepfake Detector | Checks generated or manipulated-face evidence. |
| MediaPipe Challenge | Checks fresh face and hand actions. |
| VLM Reasoner | Adds visual explanation and semantic comparison. |
| AES/JWT/Logs | Protects storage and records decisions. |

### Key Message

The architecture reduces dependence on any one model.

### Transition

"The identity spine of the system is YuNet plus ArcFace."

## Slide 5: YuNet And ArcFace

### Visual Motion

- A tilted face aligns into a stable crop.
- Embedding dots float in a 2D space.

### What To Say

"YuNet first detects the face and five landmarks. The landmarks are used to align the face to a 112 by 112 crop. ArcFace then extracts a 512-dimensional embedding. Authentication compares that embedding to the stored template."

### Formula

```text
similarity = dot(authentication_embedding, stored_template)
```

### Threshold

```text
SIMILARITY_THRESHOLD = 0.40
```

### Key Message

Alignment makes identity embeddings more stable. ArcFace verifies who the person is, not whether the capture is live.

### Transition

"That is why the next layer checks liveness."

## Slide 6: Liveness Fusion

### Visual Motion

- Signal meters rise and fall.
- Pulse chart draws a wave-like signal.

### What To Say

"Liveness is not one check. The system fuses CNN features, texture, color, moire, optical flow, micro-movement, rPPG, and optional instruction confidence."

### Signals To Explain

| Signal | What it catches |
| --- | --- |
| CNN features | unnatural texture and feature statistics |
| Texture | flat print or screen patterns |
| Color | unnatural saturation and chrominance |
| Moire | screen replay interference |
| Optical flow | static photos or unnatural motion |
| Micro-movement | lack of subtle live motion |
| rPPG | pulse-like green-channel variation |
| Instruction score | ability to follow a fresh prompt |

### Threshold

```text
FUSION_FINAL_THRESHOLD = 0.70
```

### Key Message

Video authentication is stronger than still image authentication because temporal signals become available.

### Transition

"Even if a face looks live, we still need to ask whether it might be synthetic."

## Slide 7: Deepfake Detection

### Visual Motion

- Radar chart displays low synthetic risk.
- Axes represent different artifact families.

### What To Say

"The deepfake detector estimates a probability. It combines FFT spectral analysis, EfficientNet features, boundary artifacts, eye reflection consistency, skin uniformity, color correlation, and temporal flicker."

### Artifact Families

| Family | Suspicious evidence |
| --- | --- |
| FFT | frequency bumps or high-frequency anomalies |
| CNN features | abnormal deep feature smoothness |
| Boundary | blending discontinuities |
| Eye reflections | inconsistent highlights |
| Skin | over-uniform texture |
| Color | abnormal channel correlations |
| Flicker | frame-to-frame instability |

### Threshold

```text
DEEPFAKE_FLAG_THRESHOLD = 0.30
```

### Key Message

Deepfake detection is risk estimation. It should be validated with datasets before making fixed accuracy claims.

### Transition

"A fresh active challenge adds another defense against replay."

## Slide 8: Active Challenges

### Visual Motion

- Face blinks.
- Hand waves.
- Challenge prompt changes.

### What To Say

"The optional challenge route asks the user to perform random actions. MediaPipe FaceMesh verifies face actions, and MediaPipe Hands verifies hand gestures."

### Example Instructions

- blink twice
- turn head left
- smile
- raise eyebrows
- show open palm
- wave hand
- touch nose

### Why It Helps

A printed photo cannot blink on command. An old video cannot reliably perform a newly selected instruction. A deepfake replay becomes harder if the action is unpredictable.

### Transition

"The latest VLM layer adds another type of evidence: explanation."

## Slide 9: VLM Reasoning

### Visual Motion

- Registration frames and authentication frames flank a reasoning core.
- The reasoning text rotates.
- The central grid pulses.

### What To Say

"The VLM layer compares registration reference frames with authentication frames. It reports whether they appear to show the same person, whether the authentication frames look live, whether they look authentic, and what visual concerns it sees."

### VLM Output

```json
{
  "same_person": true,
  "same_person_confidence": 0.88,
  "is_live": true,
  "liveness_confidence": 0.80,
  "is_authentic": true,
  "authenticity_confidence": 0.84,
  "overall_score": 0.85,
  "reasoning": "..."
}
```

### Important Caveat

The VLM is not the first gate. It is invoked after the traditional pipeline grants access. This saves compute and avoids relying on the VLM for basic denials.

### Transition

"All signals finally meet in the decision engine."

## Slide 10: Decision Gates

### Visual Motion

- Gate bars grow.
- Each gate displays pass-like evidence.

### What To Say

"The decision engine is threshold-based. It denies immediately if a required gate fails. Only when all required gates pass does the backend issue a JWT."

### Gate Order

1. camera/source check
2. face detection
3. liveness
4. deepfake
5. instruction compliance
6. identity match
7. grant and token

### Denial Reasons

| Reason | Meaning |
| --- | --- |
| `virtual_camera` | camera source is suspicious |
| `no_face` | no valid face was detected |
| `liveness_fail` | liveness score is too low |
| `synthetic_face` | deepfake probability is too high |
| `instruction_fail` | challenge action failed |
| `identity_mismatch` | ArcFace similarity is too low |

### Transition

"Different attacks fail at different gates."

## Slide 11: Threat Simulator

### Visual Motion

- Scenario buttons update score bars.
- Bad bars turn coral.

### What To Say

"A live user should pass identity and liveness with low deepfake risk. A printed photo may have some face similarity but fails liveness. A screen replay may show moire or motion issues. A deepfake may pass face similarity but trigger synthetic risk."

### Scenarios

| Scenario | Likely failure |
| --- | --- |
| Live user | should grant |
| Printed photo | liveness failure |
| Screen replay | liveness or synthetic-media risk |
| Deepfake | synthetic face risk |

### Key Message

Layered evidence explains why a request was denied.

### Transition

"Finally, the system protects stored data and records the decision."

## Slide 12: Security And Storage

### Visual Motion

- Vault graphic holds storage lines.
- Storage records appear as protected artifacts.

### What To Say

"The system encrypts biometric templates with AES-256-GCM, returns RS256 JWTs only on successful authentication, and stores audit logs for review."

### Storage Objects

| Object | Purpose |
| --- | --- |
| `users.embedding_enc` | encrypted ArcFace template |
| `auth_logs` | decisions, scores, flags, denial reasons |
| `challenge_logs` | issued and completed challenge metadata |
| `vlm_registrations` | VLM reference-frame metadata |
| `data/vlm_ref_frames` | VLM reference JPEG frames |

### Production Note

The current VLM reference frames should be treated as biometric data. Encrypt them before production use.

### Closing Line

"The final result is a practical, explainable, layered biometric authentication system that is stronger than face matching alone."

## Animation Design Notes

### Timing

Most animations use short cycles between 1.4 and 2.8 seconds. This keeps motion visible without making the slides feel noisy.

### Meaning Of Motion

| Motion | Meaning |
| --- | --- |
| scan line | face capture and landmark scanning |
| pulsing landmarks | five-point detection and alignment |
| moving pipeline highlight | request lifecycle |
| rising bars | embedding construction or confidence growth |
| pulse chart | rPPG signal |
| radar chart | multi-signal deepfake risk |
| blinking face | active challenge verification |
| VLM grid pulse | reasoning over image evidence |
| gate bars | threshold-based decision |

### Accessibility

The CSS includes `prefers-reduced-motion` handling. If a viewer has reduced motion enabled, animations collapse to near-static behavior.

## Suggested 8-Minute Presentation Timing

| Time | Slides | Focus |
| --- | --- | --- |
| 0:00-0:45 | 1 | problem and project purpose |
| 0:45-1:30 | 2 | full system flow |
| 1:30-2:15 | 3 | registration and encrypted template |
| 2:15-3:10 | 4-5 | model roles, YuNet, ArcFace |
| 3:10-4:20 | 6 | liveness fusion |
| 4:20-5:05 | 7 | deepfake detection |
| 5:05-5:40 | 8 | active challenges |
| 5:40-6:25 | 9 | VLM reasoning |
| 6:25-7:10 | 10 | decision gates |
| 7:10-7:45 | 11 | attack scenarios |
| 7:45-8:00 | 12 | security and conclusion |

## Q And A Preparation

### Why not use only ArcFace?

ArcFace verifies identity similarity, but it does not prove the face is live. A printed photo or screen replay can still look like the registered person. Liveness and deepfake layers address that gap.

### Why use video for login?

Video provides temporal evidence. Optical flow, flicker checks, movement consistency, and rPPG need multiple frames. Still image login has weaker liveness evidence.

### Why is the deepfake threshold low?

The current threshold is conservative. Scores above `0.30` are treated as suspicious. It should be calibrated with representative datasets before production claims.

### Is VLM mandatory?

No. VLM is optional and resource-dependent. The traditional pipeline remains usable when VLM dependencies or hardware are unavailable.

### Are biometric templates protected?

Yes. ArcFace templates are encrypted with AES-256-GCM before storage. VLM reference frames are currently stored as JPEG files and should be encrypted before production.

### Can the system detect every attack?

No biometric system should claim that without extensive evaluation. This project implements layered defenses and produces auditable scores, but dataset-backed validation is required for accuracy claims.

## Demo Checklist

Before presenting:

1. Open `docs/interactive_auth_presentation/index.html` in a browser.
2. Test next, previous, replay, and keyboard controls.
3. Confirm slide 2 pipeline animation runs.
4. Confirm slide 7 radar canvas draws.
5. Confirm slide 11 simulator buttons update bars.
6. Prepare one verbal example for each denial reason.
7. Mention the current VLM registration frontend/backend contract note if showing VLM registration.

