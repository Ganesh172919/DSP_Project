# AI Models Guide

DeepShield Guardian uses an AI-adjacent biometric pipeline today and is explicitly structured so stronger production models can replace the current heuristic baselines.
This guide explains what is implemented now, what each subsystem estimates, why those signals matter, and where trained models fit into the architecture.

## Reading This Guide

- Read this file first for the end-to-end AI story.
- Read `docs/ai-model-catalog.md` for candidate model families, datasets, evaluation plans, and serving strategy.
- Read `docs/ai-model-appendix.md` for challenge-level references, metric glossary, templates, and checklists.
- Treat future-model references as roadmap guidance, not as claims about the current codebase.

## Core Positioning

- The current repository implements a serious baseline, not a certified biometric engine.
- The current recognition path is deterministic and geometry-driven, not ArcFace-grade recognition.
- The current PAD and deepfake paths are heuristic but intentionally organized like future model-serving boundaries.
- The current liveness path already spans multiple challenge families instead of relying only on blink detection.
- The current decision path is policy-oriented and can absorb stronger model signals with minimal API changes.

## AI Stack At A Glance

1. Browser sensing captures camera frames and extracts face and hand landmarks.
2. The API converts landmarks into dense geometric biometric features.
3. A deterministic embedding is generated for baseline recognition.
4. Enrollment templates store step-wise embeddings and averaged metrics.
5. Authentication compares the live frame against the template.
6. PAD heuristics score replay, print, and mask realism.
7. Deepfake heuristics score frequency, boundaries, eye reflections, mouth interior, temporal stability, and pulse plausibility.
8. Liveness challenge verifiers score instructed user actions.
9. The decision engine fuses stage scores under fail-secure policy rules.

## Current Components

### Browser landmark sensing

- Implemented now: MediaPipe face and hand landmarks in the browser.
- Why it matters: Supplies client metrics and challenge cues before the server scores a frame.
- Current home: apps/web/src/lib/use-biometric-capture.ts
- Present takeaway: Lightweight sensing and feedback.
- Upgrade path: Future path: add model-backed quality estimation and tracking confidence.
- AI implication: the current code already defines the contract a stronger model should satisfy.
- Engineering implication: preserve output semantics so policy code and audit traces stay stable.
- Product implication: document clearly whether each score comes from heuristics, deterministic geometry, or a trained model.

### Geometric feature extractor

- Implemented now: Large face, eye, brow, nose, mouth, pose, and skin metric set.
- Why it matters: Creates interpretable biometric measurements from landmarks and optional image patches.
- Current home: services/api/app/services/feature_extractor.py
- Present takeaway: Explainable feature engineering.
- Upgrade path: Future path: combine with learned embeddings and quality heads.
- AI implication: the current code already defines the contract a stronger model should satisfy.
- Engineering implication: preserve output semantics so policy code and audit traces stay stable.
- Product implication: document clearly whether each score comes from heuristics, deterministic geometry, or a trained model.

### Deterministic embedding builder

- Implemented now: A normalized landmark subset becomes a fixed 128-d vector.
- Why it matters: Acts as the baseline recognition encoder while preserving a stable contract.
- Current home: services/api/app/services/feature_extractor.py and services/ml-face/app/main.py
- Present takeaway: Reproducible placeholder for recognition.
- Upgrade path: Future path: replace with ArcFace, AdaFace, MagFace, or similar.
- AI implication: the current code already defines the contract a stronger model should satisfy.
- Engineering implication: preserve output semantics so policy code and audit traces stay stable.
- Product implication: document clearly whether each score comes from heuristics, deterministic geometry, or a trained model.

### Template builder

- Implemented now: Enrollment samples are grouped by capture step and averaged.
- Why it matters: Stores a protected multi-view reference for later comparisons.
- Current home: services/api/app/services/feature_extractor.py
- Present takeaway: Step-wise template structure.
- Upgrade path: Future path: outlier rejection, uncertainty, and quality-weighted averaging.
- AI implication: the current code already defines the contract a stronger model should satisfy.
- Engineering implication: preserve output semantics so policy code and audit traces stay stable.
- Product implication: document clearly whether each score comes from heuristics, deterministic geometry, or a trained model.

### Template comparator

- Implemented now: Live frames are compared with cosine similarity and scalar-feature agreement.
- Why it matters: Separates global identity similarity from interpretable feature consistency.
- Current home: services/api/app/services/feature_extractor.py
- Present takeaway: Recognition plus feature verification.
- Upgrade path: Future path: calibrated matching and uncertainty-aware scoring.
- AI implication: the current code already defines the contract a stronger model should satisfy.
- Engineering implication: preserve output semantics so policy code and audit traces stay stable.
- Product implication: document clearly whether each score comes from heuristics, deterministic geometry, or a trained model.

### Presentation attack detection

- Implemented now: Screen replay, printed photo, and 3D mask heuristics.
- Why it matters: Provides the realism gate before recognition and liveness are trusted.
- Current home: services/api/app/services/pad_detector.py
- Present takeaway: Interpretable passive PAD baseline.
- Upgrade path: Future path: supervised PAD with domain generalization and temporal cues.
- AI implication: the current code already defines the contract a stronger model should satisfy.
- Engineering implication: preserve output semantics so policy code and audit traces stay stable.
- Product implication: document clearly whether each score comes from heuristics, deterministic geometry, or a trained model.

### Deepfake detector

- Implemented now: Frequency, boundary, eye-reflection, mouth, temporal, and rPPG checks.
- Why it matters: Adds synthetic-media forensics to the authentication flow.
- Current home: services/api/app/services/deepfake_detector.py
- Present takeaway: Multi-cue forensic baseline.
- Upgrade path: Future path: learned image and video forensics models.
- AI implication: the current code already defines the contract a stronger model should satisfy.
- Engineering implication: preserve output semantics so policy code and audit traces stay stable.
- Product implication: document clearly whether each score comes from heuristics, deterministic geometry, or a trained model.

### Temporal analyzer

- Implemented now: Tracks landmark jitter, embedding stability, and brightness stability.
- Why it matters: Adds rolling-window evidence instead of only frame-level evidence.
- Current home: services/api/app/services/deepfake_detector.py
- Present takeaway: Stateful temporal heuristics.
- Upgrade path: Future path: sequence encoders and optical-flow consistency models.
- AI implication: the current code already defines the contract a stronger model should satisfy.
- Engineering implication: preserve output semantics so policy code and audit traces stay stable.
- Product implication: document clearly whether each score comes from heuristics, deterministic geometry, or a trained model.

### rPPG analyzer

- Implemented now: Green-channel forehead pulse plausibility signal.
- Why it matters: Adds biological realism evidence when enough frames are available.
- Current home: services/api/app/services/deepfake_detector.py
- Present takeaway: Low-cost physiology cue.
- Upgrade path: Future path: motion-robust learned rPPG quality and pulse models.
- AI implication: the current code already defines the contract a stronger model should satisfy.
- Engineering implication: preserve output semantics so policy code and audit traces stay stable.
- Product implication: document clearly whether each score comes from heuristics, deterministic geometry, or a trained model.

## Decision Stages

### Face Detection

- Stage key: `face_detection`
- Weight: `0.08`
- Threshold: `0.45`
- Failure message: Face not reliably detected in frame
- Calibration note: score meaning should remain stable across model versions.
- Policy note: strong scores in one stage should never hide a hard failure in another stage.
- Monitoring note: any rollout that shifts this stage distribution should trigger threshold review.

### Presentation Attack Detection

- Stage key: `presentation_attack_detection`
- Weight: `0.18`
- Threshold: `0.5`
- Failure message: Frame shows signs of spoofing (screen, photo, or mask)
- Calibration note: score meaning should remain stable across model versions.
- Policy note: strong scores in one stage should never hide a hard failure in another stage.
- Monitoring note: any rollout that shifts this stage distribution should trigger threshold review.

### Facial Recognition Match

- Stage key: `recognition`
- Weight: `0.25`
- Threshold: `0.6`
- Failure message: Face geometry does not match enrolled template
- Calibration note: score meaning should remain stable across model versions.
- Policy note: strong scores in one stage should never hide a hard failure in another stage.
- Monitoring note: any rollout that shifts this stage distribution should trigger threshold review.

### Granular Feature Verification

- Stage key: `feature_verification`
- Weight: `0.1`
- Threshold: `0.55`
- Failure message: Biometric feature comparison below confidence threshold
- Calibration note: score meaning should remain stable across model versions.
- Policy note: strong scores in one stage should never hide a hard failure in another stage.
- Monitoring note: any rollout that shifts this stage distribution should trigger threshold review.

### Liveness Verification

- Stage key: `liveness`
- Weight: `0.22`
- Threshold: `0.45`
- Failure message: Challenge-response liveness verification incomplete or failed
- Calibration note: score meaning should remain stable across model versions.
- Policy note: strong scores in one stage should never hide a hard failure in another stage.
- Monitoring note: any rollout that shifts this stage distribution should trigger threshold review.

### Deepfake Scan

- Stage key: `deepfake_scan`
- Weight: `0.17`
- Threshold: `0.45`
- Failure message: Frame shows indicators of synthetic generation
- Calibration note: score meaning should remain stable across model versions.
- Policy note: strong scores in one stage should never hide a hard failure in another stage.
- Monitoring note: any rollout that shifts this stage distribution should trigger threshold review.

## Aggregate Policy

- Current aggregate threshold: `0.62`
- Current anomaly-review threshold: `0.78`
- The aggregate rule is intentionally paired with per-stage gates.
- This prevents a very strong recognition score from hiding a spoofing or deepfake failure.
- Future model rollouts should preserve the all-pass safety posture unless a formal review approves a different policy.

## Recognition Pipeline

- Recognition begins with landmark normalization rather than raw pixel embeddings.
- A curated subset of landmarks is centered and scaled before deterministic projection.
- This baseline behaves like a simple geometric embedding rather than a learned identity manifold.
- Its main strength is explainability and reproducibility.
- Its main weakness is limited robustness to pose, expression, camera distortion, and demographic variation.
- The stored template is multi-step rather than single-view, which partially offsets viewpoint variance.
- Scalar metric comparison adds an interpretable second channel beside cosine similarity.
- Recognition and feature verification should remain conceptually separate in future learned-model upgrades.
- A production system would likely use a learned encoder for recognition and keep some handcrafted metrics for explainability.
- Calibration should include impostor and genuine score distributions across device classes and lighting bands.

## PAD Pipeline

### Screen replay detector

- Uses FFT-derived periodicity cues to estimate moire-like artifacts.
- Examines high-frequency energy because display replays alter natural image detail.
- Uses a basic color-temperature heuristic as a weak realism cue.
- Should eventually be paired with supervised PAD models trained on replay attacks across devices.

### Printed photo detector

- Scores paper-like texture noise, limited gamut, and edge sharpness behavior.
- Captures a different failure mode from screen replay because print artifacts are physical rather than emissive.
- Could later be paired with pseudo-depth or binocular cues if hardware expands.
- Benefits from datasets with varied print materials, finishes, and capture distances.

### 3D mask detector

- Uses multi-scale LBP entropy, highlight behavior, and color variation as mask realism cues.
- This is a sensible baseline for cheap masks but not enough for high-end silicone attacks.
- A production upgrade should consider texture-supervised or depth-supervised anti-spoofing models.
- Specular behavior is useful but too lighting-dependent to dominate decisions alone.

## Deepfake Pipeline

### Frequency-domain analysis

- Checks whether the spectrum resembles a natural 1/f falloff.
- Measures high-frequency energy ratio because synthetic imagery often smooths fine detail.
- Looks for periodicity that may arise from generator up-sampling artifacts.
- Aligns well with future frequency-aware models such as F3-Net-like approaches.

### Face boundary analysis

- Searches for seam-like edges and resolution mismatches around the face region.
- Is especially relevant to face swaps and pasted-face artifacts.
- Should remain visible as a diagnostic even after moving to learned forensic models.
- Supports human review because boundary artifacts are intuitive to explain.

### Temporal and rPPG cues

- Track landmark jitter, embedding stability, brightness behavior, and pulse plausibility over time.
- Help expose feeds that are too stable, too jittery, or physiologically implausible.
- Grow in value as authentication sessions become longer or challenge-rich.
- Should be strengthened with motion-robust sequence models rather than discarded.

## How To Improve The Model

### Recognition Improvements

- Replace the deterministic landmark projection with a learned face-recognition encoder such as ArcFace, AdaFace, MagFace, or a compact CPU-friendly alternative.
- Keep the current step-wise enrollment structure so the identity model can evolve without breaking the storage contract.
- Add face alignment before embedding generation so pose and crop variation affect the embedding less.
- Introduce per-frame quality estimation and reject low-information frames before they enter enrollment or matching.
- Build multi-frame authentication embeddings instead of relying on only one frame at match time.
- Calibrate similarity thresholds on the actual target devices instead of reusing values from public benchmarks.
- Keep explainable geometric metrics beside the learned encoder so support and audit teams still have interpretable evidence.
- Add outlier rejection during enrollment so a single bad capture does not dilute the stored template.
- Store model version metadata with templates if the recognition encoder becomes a production dependency.
- Measure false reject and false accept behavior by pose, blur, lighting, glasses, and demographic slice before rolling out a stronger model.

### PAD Improvements

- Move from purely heuristic PAD to supervised RGB anti-spoofing models that are trained on print, replay, and mask attacks.
- Retain the current moire, texture, and highlight diagnostics as secondary explanations even after a neural PAD model is introduced.
- Add sequence-level PAD so the platform can use temporal motion and realism cues instead of only one frame.
- Expand spoof validation to real attack instruments that match the project environment, especially phone screens, laptops, and glossy prints.
- Tune PAD thresholds separately for strong-light, dim-light, and compressed-video conditions if score drift is large.
- Add capture-quality conditioning so PAD is more conservative when frames are too blurry or too dark.
- Measure APCER, BPCER, and attack-type-specific performance instead of only a single aggregate metric.
- Consider pseudo-depth or surface-normal estimation if the system later supports more advanced cameras.

### Deepfake Improvements

- Add a learned image-forensics model first, then a sequence model for manipulated video and generative avatars.
- Preserve the current frequency, boundary, eye-reflection, and mouth-interior analyses as interpretable supporting detail.
- Include conferencing-tool compression, virtual camera pipelines, and low-bitrate clips in evaluation because those are common operational distortions.
- Add confidence calibration so deepfake scores from different model versions remain comparable.
- Use temporal reasoning over several seconds instead of relying only on per-frame artifact detection.
- Improve rPPG quality estimation so physiological evidence is ignored gracefully when the signal is too weak.
- Log enough nonsecret evidence to study borderline synthetic-media cases without storing unnecessary sensitive content.
- Re-evaluate deepfake models regularly because attack generation quality changes faster than traditional biometric conditions.

### Liveness Improvements

- Keep the current challenge catalog but add sequence models that learn whether the prompted action happened naturally and on time.
- Increase prompt diversity so attackers cannot overfit to a narrow challenge set.
- Introduce adaptive challenge selection based on risk, device familiarity, and recent failed attempts.
- Add better hand-face interaction modeling for touch-nose, wave, and finger-count prompts.
- Support accessibility-aware challenge substitution instead of simply removing difficult prompts.
- Track challenge completion latency and prompt confusion so usability regressions are visible early.
- Penalize suspiciously perfect or repeated response timing patterns that resemble prerecorded material.
- Use multi-signal liveness scoring so eye, mouth, head, and temporal cues can reinforce each other when one signal is weak.

### Fusion And Policy Improvements

- Replace fixed raw-score fusion with calibrated postprocessing once stronger models are added.
- Keep hard fail-secure gates for clear spoofing, deepfake, or recognition failures even if a learned fusion layer is introduced.
- Represent missing evidence explicitly rather than pretending a missing signal equals a neutral score.
- Separate review decisions from hard denials so borderline outcomes can be handled with human oversight.
- Add device trust, recent failure count, and session context as controlled policy inputs instead of ad hoc adjustments.
- Recalibrate the aggregate threshold after every meaningful upstream model change.

## How To Make Authentication More Functional

- Add adaptive challenge selection so low-risk users see simpler flows and high-risk sessions get stronger verification.
- Support progressive authentication where a user can pass a low-risk gate quickly and only escalate when risk indicators appear.
- Introduce a clearer enrollment quality workflow so users know exactly why a capture was rejected and how to fix it.
- Store richer audit context so administrators can inspect why a session passed, failed, or was flagged for review.
- Add explicit accessibility profiles for users who cannot comfortably perform head-turn, hand, or expression challenges.
- Add retry-state awareness so the system can change prompts instead of repeating the same failure pattern.
- Improve user guidance messages so they are short, actionable, and tied to real capture problems such as blur, darkness, framing, or occlusion.
- Add session continuity for interrupted authentication attempts so users do not restart unnecessarily after minor connection issues.
- Improve fallback behavior when optional microservices are unavailable so authentication degrades safely but predictably.
- Add structured per-stage telemetry so product and security teams can see where users struggle most.
- Provide administrators with per-stage analytics instead of only final decision counts.
- Add model version and policy version to audit events so historical sessions remain explainable after rollouts.
- Separate user-facing failure language from security-facing anomaly language so the UX stays clear without exposing attacker hints.
- Add explicit device and browser capability detection so unsupported environments fail early with guidance instead of confusing mid-flow errors.

## How To Make Authentication More Efficient

### Frontend Efficiency

- Reuse landmark results across multiple checks so the browser does not recompute similar geometry several times per frame.
- Reduce frame-analysis frequency dynamically when the face is stable and challenge progress is already clear.
- Crop or downscale frames before upload when full-resolution images do not improve server-side scoring.
- Send only the fields required for the current stage instead of the full observation payload every time.
- Pause nonessential processing when the face is not present so idle sessions consume fewer resources.
- Use staged quality gates in the browser so obviously unusable frames never reach expensive server logic.

### Backend Efficiency

- Cache decoded frame artifacts that are reused by PAD, deepfake, and quality analysis within the same request.
- Compute shared low-level image statistics once and feed them to multiple subsystems.
- Move to batched inference if learned models are introduced in `ml-face` or `ml-risk`.
- Reuse temporal state across frames efficiently instead of re-deriving prior observations from storage.
- Store compact derived features for review and analytics instead of repeatedly reprocessing the same raw session data.
- Introduce asynchronous microservice calls only when the policy can tolerate partial waiting and late-arriving evidence.
- Make quality gating early so expensive model calls are skipped when the frame is unusable.

### Model Efficiency

- Choose smaller recognition and PAD models first if CPU latency is a hard constraint.
- Quantize or export models to ONNX when the accuracy loss is acceptable and latency improves materially.
- Run heavy deepfake or sequence models only after cheap heuristics indicate elevated risk.
- Separate always-on models from escalation-only models so the common authentication path stays fast.
- Measure latency by stage and by device class before optimizing blindly.
- Prefer one well-calibrated model over several overlapping models if the ensemble cost is not justified by measurable security gain.

### Data And Storage Efficiency

- Keep encrypted templates compact and versioned so matching remains fast and schema changes stay manageable.
- Store only the minimum review artifacts needed for incident analysis and compliance.
- Expire temporary session data aggressively once the audit requirements are satisfied.
- Avoid retaining duplicate frame payloads when derived metrics already capture the needed evidence.
- Partition analytics and operational data so high-volume telemetry does not slow authentication transactions.

## Practical Implementation Order

1. Upgrade recognition first with a calibrated learned encoder while keeping the existing template structure.
2. Add per-frame quality estimation and stronger enrollment filtering so every downstream model sees cleaner input.
3. Introduce supervised PAD and keep the current heuristic outputs as diagnostics.
4. Add an image-level deepfake model, then a temporal deepfake model for higher-risk flows.
5. Improve liveness with adaptive challenge selection and learned sequence validation.
6. Recalibrate fusion and policy thresholds after the upstream models stabilize.
7. Add monitoring, shadow deployment, rollback rules, and fairness review before enforcing stricter gates broadly.

## Recommended Success Metrics

- Lower false rejects without increasing spoof acceptance.
- Lower average authentication latency for clean sessions.
- Higher completion rate on mobile and laptop webcams.
- Better performance under low light, glasses, and compressed-video conditions.
- More stable score distributions across devices and browsers.
- Smaller review queue for nonmalicious borderline sessions.
- Clearer administrator visibility into stage-level failures and model drift.
