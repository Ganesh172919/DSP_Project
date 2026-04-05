import { useMemo, useState } from "react";
import {
  completeAuthentication,
  startAuthentication,
  submitAuthenticationFrame,
} from "../lib/api";
import type {
  AuthenticationStateResponse,
  ChallengeDefinition,
  LiveChallengeTelemetry,
  LiveProcessingTelemetry,
  StageResult,
} from "../lib/types";
import { useBiometricCapture } from "../lib/use-biometric-capture";

const CHALLENGE_ICONS: Record<string, string> = {
  eye: "E",
  mouth: "M",
  head: "H",
  expression: "X",
  distance: "D",
  combined: "C",
  cognitive: "K",
};

const STAGE_ICONS: Record<string, string> = {
  face_detection: "FD",
  presentation_attack_detection: "PAD",
  recognition: "REC",
  feature_verification: "FV",
  liveness: "LIVE",
  deepfake_scan: "DF",
};

const BASE_CAPTURE_STEPS = [
  "Enter the same email used during registration.",
  "Position your face inside the oval guide — laptops are fine.",
  "Follow the on-screen prompt, then return to a neutral face.",
];

const FRAME_DELAY_MS = 850;
const PRE_FLIGHT_STABLE_CHECKS = 2;
const EXTRA_FRAME_LIMIT = 6;

type CoachState = {
  level: "good" | "warn" | "bad";
  headline: string;
  detail: string;
  steps: string[];
  preflightReady: boolean;
  captureReady: boolean;
  guideClassName: string;
};

function formatRatioPercent(value: number | null | undefined, digits = 0) {
  return typeof value === "number" ? `${(value * 100).toFixed(digits)}%` : "--";
}

function formatScoreOutOfHundred(value: number | null | undefined, digits = 1) {
  return typeof value === "number" ? `${value.toFixed(digits)} / 100` : "--";
}

function readNumber(metrics: Record<string, number | boolean | string | null>, key: string, fallback = 0) {
  const value = metrics[key];
  return typeof value === "number" ? value : fallback;
}

function dedupe(items: string[]) {
  const unique: string[] = [];
  const seen = new Set<string>();

  for (const item of items) {
    const trimmed = item.trim();
    if (!trimmed || seen.has(trimmed)) {
      continue;
    }

    seen.add(trimmed);
    unique.push(trimmed);
  }

  return unique;
}

function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

function buildCaptureCoach(metrics: Record<string, number | boolean | string | null>): CoachState {
  const facePresent = Boolean(metrics.face_present);
  const faceSizeRatio = readNumber(metrics, "face_size_ratio");
  const faceCenterX = readNumber(metrics, "face_center_x", 0.5);
  const eyeLineY = readNumber(metrics, "eye_line_y", readNumber(metrics, "face_center_y", 0.5));
  const topMargin = readNumber(metrics, "face_top_margin");
  const bottomMargin = readNumber(metrics, "face_bottom_margin");
  const roll = Math.abs(readNumber(metrics, "roll"));
  const qualityHint = String(metrics.quality_hint ?? "");

  if (!facePresent) {
    return {
      level: "bad",
      headline: "Position your face inside the guide",
      detail: "Only one face should be visible, with your forehead and chin fully inside the frame.",
      steps: [
        "Look directly at the camera.",
        "Move closer until your face clearly fills the guide.",
        "Keep the background steady while the detectors lock on.",
      ],
      preflightReady: false,
      captureReady: false,
      guideClassName: "face-guide--bad",
    };
  }

  const adjustments: string[] = [];

  if (faceSizeRatio < 0.05) {
    adjustments.push("Move a bit closer to the camera.");
  }
  if (eyeLineY > 0.50 || bottomMargin < 0.05) {
    adjustments.push("Raise the camera or tilt your laptop screen upward.");
  } else if (eyeLineY < 0.15 || topMargin < 0.02) {
    adjustments.push("Lower the camera slightly so your forehead is not cropped.");
  }
  if (faceCenterX < 0.30) {
    adjustments.push("Move your face to the right.");
  } else if (faceCenterX > 0.70) {
    adjustments.push("Move your face to the left.");
  }
  if (roll > 15) {
    adjustments.push("Straighten your head.");
  }
  if (
    qualityHint &&
    qualityHint !== "Ready" &&
    qualityHint !== "No face" &&
    !adjustments.includes(qualityHint)
  ) {
    adjustments.push(qualityHint);
  }

  const preflightReady =
    faceSizeRatio >= 0.05 &&
    faceCenterX >= 0.30 &&
    faceCenterX <= 0.70 &&
    eyeLineY >= 0.15 &&
    eyeLineY <= 0.55 &&
    bottomMargin >= 0.04 &&
    roll <= 15;

  const captureReady =
    faceSizeRatio >= 0.04 &&
    faceCenterX >= 0.22 &&
    faceCenterX <= 0.78 &&
    eyeLineY >= 0.10 &&
    eyeLineY <= 0.60 &&
    bottomMargin >= 0.02;

  if (!adjustments.length) {
    return {
      level: "good",
      headline: "Camera position looks good",
      detail: "Keep your face inside the guide, follow one prompt at a time, and return to neutral after each action.",
      steps: [
        "Keep both eyes visible.",
        "Move only the feature requested by the prompt.",
        "Pause briefly after each action so the frame stays sharp.",
      ],
      preflightReady,
      captureReady,
      guideClassName: "face-guide--good",
    };
  }

  return {
    level: preflightReady ? "warn" : "bad",
    headline: adjustments[0].replace(/\.$/, ""),
    detail: adjustments.length > 1 ? adjustments[1] : "Make this adjustment before starting the guided scan.",
    steps: adjustments,
    preflightReady,
    captureReady,
    guideClassName: preflightReady ? "face-guide--warn" : "face-guide--bad",
  };
}

function buildChallengeActionSteps(challenge?: ChallengeDefinition) {
  if (!challenge) {
    return BASE_CAPTURE_STEPS;
  }

  const categoryTip =
    challenge.category === "eye"
      ? "Keep your head still and move only your eyes."
      : challenge.category === "head"
        ? "Move slowly and keep your full face inside the guide."
        : challenge.category === "mouth" || challenge.category === "expression"
          ? "Keep looking at the camera while you move only the requested feature."
          : challenge.category === "cognitive"
            ? "Bring one hand in without covering your eyes or mouth."
            : "Move naturally, then return to a neutral face.";

  return [
    challenge.description,
    categoryTip,
    "Return to a neutral face before the next prompt.",
  ];
}

function buildFriendlyError(error: unknown) {
  const message = error instanceof Error ? error.message : "Authentication sequence failed";

  if (message.includes("No account found")) {
    return "No account found for this email. Use the same email you used during registration.";
  }
  if (message.includes("temporarily locked")) {
    return message;
  }
  if (message.includes("expired")) {
    return "This scan expired. Start a fresh attempt and follow the guide from the beginning.";
  }

  return message;
}

export function AuthenticatePage() {
  const { videoRef, canvasRef, ready, loading, error, captureSnapshot, snapshot } = useBiometricCapture();
  const [email, setEmail] = useState("");
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [challenges, setChallenges] = useState<ChallengeDefinition[]>([]);
  const [activeChallenge, setActiveChallenge] = useState(0);
  const [stageResults, setStageResults] = useState<StageResult[]>([]);
  const [finalState, setFinalState] = useState<AuthenticationStateResponse | null>(null);
  const [liveTelemetry, setLiveTelemetry] = useState<LiveProcessingTelemetry | null>(null);
  const [busy, setBusy] = useState(false);
  const [running, setRunning] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [message, setMessage] = useState(
    "Enter your registered email, then align your face with the guide and start the scan."
  );
  const [attemptsInfo, setAttemptsInfo] = useState({ number: 0, remaining: 3 });
  const [emailStatus, setEmailStatus] = useState<'idle' | 'checking' | 'found' | 'not_found' | 'error'>('idle');

  const currentChallenge = useMemo(() => challenges[activeChallenge], [activeChallenge, challenges]);
  const visibleTelemetry = finalState?.live_telemetry ?? liveTelemetry;
  const normalizedEmail = email.trim().toLowerCase();
  const captureCoach = useMemo(
    () => buildCaptureCoach(snapshot.client_metrics),
    [snapshot.client_metrics]
  );
  const challengeSteps = useMemo(
    () => buildChallengeActionSteps(currentChallenge),
    [currentChallenge]
  );

  const challengeTelemetry = useMemo(() => {
    const telemetryById = new Map((visibleTelemetry?.challenge_results ?? []).map((item) => [item.id, item]));
    return challenges.map((challenge) => {
      const existing = telemetryById.get(challenge.id);
      if (existing) {
        return existing;
      }
      return {
        id: challenge.id,
        title: challenge.title,
        frames_processed: 0,
        progress: 0,
        status: "pending",
        message: "Waiting for guided scan",
      } as LiveChallengeTelemetry;
    });
  }, [challenges, visibleTelemetry]);

  const visibleStageResults = stageResults.length
    ? stageResults
    : [{
        stage: "face_detection" as const,
        score: readNumber(snapshot.client_metrics, "alignment_score", snapshot.client_metrics.face_present ? 0.45 : 0),
        passed: captureCoach.preflightReady,
        message: captureCoach.headline,
        label: "Camera Alignment",
        weight: 0.1,
        threshold: 0.7,
      }];

  const telemetryGuidance = dedupe([
    ...(visibleTelemetry?.guidance ?? []),
    ...(running ? challengeSteps : captureCoach.steps),
  ]);

  async function handleStartAuthentication() {
    if (!normalizedEmail) {
      setMessage("Enter the same email you used during registration.");
      return;
    }

    setBusy(true);
    setAttemptId(null);
    setChallenges([]);
    setFinalState(null);
    setLiveTelemetry(null);
    setStageResults([]);
    setEmailStatus('checking');

    try {
      const response = await startAuthentication({ email: normalizedEmail });
      setEmail(normalizedEmail);
      setAttemptId(response.attempt_id);
      setChallenges(response.challenges);
      setActiveChallenge(0);
      setAttemptsInfo({
        number: response.attempt_number || 1,
        remaining: response.max_attempts || 3,
      });
      setEmailStatus('found');
      setMessage(
        "✅ Account found! Position your face inside the guide, then click 'Start Guided Scan'."
      );
    } catch (cause) {
      const errMsg = buildFriendlyError(cause);
      setEmailStatus(errMsg.includes("No account") ? 'not_found' : 'error');
      setMessage(errMsg);
    } finally {
      setBusy(false);
    }
  }

  async function runChallengeSequence() {
    if (!attemptId || !challenges.length) {
      setMessage("Check your registered email first.");
      return;
    }
    if (!captureCoach.preflightReady) {
      setMessage(`Please adjust: ${captureCoach.headline}. Then try again.`);
      return;
    }

    setBusy(true);
    setRunning(true);
    setFinalState(null);
    setMessage("Guided scan started. Keep your face inside the guide and follow one prompt at a time.");

    try {
      for (let challengeIndex = 0; challengeIndex < challenges.length; challengeIndex += 1) {
        const challenge = challenges[challengeIndex];
        const steps = buildChallengeActionSteps(challenge);

        setActiveChallenge(challengeIndex);
        setCountdown(challenge.duration_seconds);
        setMessage(
          `Step ${challengeIndex + 1} of ${challenges.length}: ${challenge.title}. ${steps[0]}`
        );

        let stableChecks = 0;
        while (stableChecks < PRE_FLIGHT_STABLE_CHECKS) {
          const warmupSnapshot = captureSnapshot();
          const warmupCoach = buildCaptureCoach(warmupSnapshot.client_metrics);

          if (warmupCoach.preflightReady) {
            stableChecks += 1;
          } else {
            stableChecks = 0;
            setMessage(`Adjust before ${challenge.title.toLowerCase()}: ${warmupCoach.headline}.`);
          }

          await sleep(350);
        }

        const targetFrames = Math.max(4, challenge.duration_seconds);
        let acceptedFrames = 0;
        let submittedFrames = 0;

        while (acceptedFrames < targetFrames && submittedFrames < targetFrames + EXTRA_FRAME_LIMIT) {
          const payload = captureSnapshot();
          const frameCoach = buildCaptureCoach(payload.client_metrics);
          setCountdown(Math.max(0, challenge.duration_seconds - acceptedFrames));

          if (!frameCoach.captureReady) {
            setMessage(`Pause and adjust: ${frameCoach.headline}.`);
            await sleep(450);
            continue;
          }

          const response = await submitAuthenticationFrame(attemptId, {
            step: "authentication_live_frame",
            challenge_id: challenge.id,
            frame_b64: payload.frame_b64,
            landmarks: payload.landmarks,
            hand_landmarks: payload.hand_landmarks,
            client_metrics: payload.client_metrics,
            captured_at: new Date().toISOString(),
          });

          submittedFrames += 1;
          setStageResults(response.stage_results);
          setLiveTelemetry(response.live_telemetry ?? null);

          const serverGuidance = response.live_telemetry?.guidance ?? [];
          const serverNeedsRetry = serverGuidance.some((item) => item.toLowerCase().includes("blurry"));
          const qualityScore = response.live_telemetry?.quality_score ?? 0;
          const challengePassed = response.live_telemetry?.current_challenge_passed === true;
          const usableFrame = !serverNeedsRetry && qualityScore >= 30;

          if (usableFrame) {
            acceptedFrames += 1;
            setMessage(
              `Step ${challengeIndex + 1} of ${challenges.length}: ${challenge.title}. ${steps[1]}`
            );
          } else {
            const retryMessage = serverGuidance[0] ?? "Hold still for a clearer frame";
            setMessage(`${retryMessage}. Repeating this step.`);
          }

          if (challengePassed && acceptedFrames >= Math.max(2, Math.ceil(targetFrames / 2))) {
            acceptedFrames = targetFrames;
            setMessage(
              `Step ${challengeIndex + 1} complete. Return to a neutral face for the next prompt.`
            );
          }

          await sleep(serverNeedsRetry ? 1000 : FRAME_DELAY_MS);
        }

        if (acceptedFrames < targetFrames) {
          setMessage(
            "Could not capture enough clear frames. Check your lighting and camera position, then try again."
          );
          // Don't throw — allow user to try again
          break;
        }
      }

      const decision = await completeAuthentication(attemptId);
      setFinalState(decision);
      setLiveTelemetry(decision.live_telemetry ?? null);
      setStageResults(decision.stage_results);
      setAttemptsInfo((previous) => ({
        ...previous,
        remaining: decision.attempts_remaining ?? previous.remaining,
      }));
      setMessage(
        decision.authenticated
          ? "Authentication successful."
          : `Authentication denied. ${(decision.denial_reasons?.[0] ?? "The scan did not meet the required thresholds.")}`
      );
    } catch (cause) {
      setMessage(buildFriendlyError(cause));
    } finally {
      setBusy(false);
      setRunning(false);
      setCountdown(0);
    }
  }

  return (
    <section className="two-column">
      <article className="panel animate-in">
        <span className="kicker">Live Verification Cascade</span>
        <h1 style={{ fontSize: "1.8rem", marginTop: "0.8rem" }}>Authenticate</h1>
        <p className="lead">
          Enter your email, position your face in the guide, then complete the liveness scan.
        </p>

        <div className="field-grid" style={{ marginTop: "1rem" }}>
          <label className="field">
            <span>Registered email</span>
            <input
              placeholder="john@example.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
        </div>

        <div className="button-row">
          <button
            className="button button--primary"
            disabled={busy || !normalizedEmail}
            onClick={handleStartAuthentication}
          >
            {emailStatus === 'checking' ? '⏳ Checking...' : emailStatus === 'found' ? '✅ Email Verified' : 'Check Registered Email'}
          </button>
          <button
            className="button"
            disabled={busy || !attemptId || !ready || running || !captureCoach.preflightReady}
            onClick={runChallengeSequence}
          >
            {captureCoach.preflightReady ? "▶ Start Guided Scan" : "Align Face To Start"}
          </button>
          {(finalState || emailStatus === 'error' || emailStatus === 'not_found') && (
            <button
              className="button"
              disabled={busy || running}
              onClick={() => {
                setAttemptId(null);
                setChallenges([]);
                setFinalState(null);
                setLiveTelemetry(null);
                setStageResults([]);
                setEmailStatus('idle');
                setAttemptsInfo({ number: 0, remaining: 3 });
                setMessage("Enter your registered email, then align your face with the guide and start the scan.");
              }}
            >
              🔄 Start Over
            </button>
          )}
        </div>

        {/* Email status indicator */}
        {emailStatus !== 'idle' && (
          <div style={{ marginTop: '0.6rem' }}>
            <span className={`status-pill status-pill--${
              emailStatus === 'found' ? 'good' :
              emailStatus === 'checking' ? 'warn' : 'bad'
            }`} style={{ fontSize: '0.85rem' }}>
              {emailStatus === 'checking' && '🔍 Looking up your account...'}
              {emailStatus === 'found' && `✅ Account found for ${normalizedEmail}`}
              {emailStatus === 'not_found' && '❌ No account found — check your email address'}
              {emailStatus === 'error' && '⚠️ Error checking account — try again'}
            </span>
          </div>
        )}

        <div className="signal-list" style={{ marginTop: "1rem" }}>
          {BASE_CAPTURE_STEPS.map((item, index) => (
            <div className="timeline-card" key={item}>
              <strong>Step {index + 1}</strong>
              <p className="subtle">{item}</p>
            </div>
          ))}
        </div>

        {attemptsInfo.number > 0 && (
          <div style={{ marginTop: "0.8rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <span className="kicker">Attempt #{attemptsInfo.number}</span>
            <span className={`kicker ${attemptsInfo.remaining <= 1 ? "kicker--danger" : "kicker--purple"}`}>
              {attemptsInfo.remaining} remaining
            </span>
          </div>
        )}

        {running && currentChallenge && (
          <div className="challenge-display" style={{ marginTop: "1rem" }}>
            <div className="challenge-display__icon">
              {CHALLENGE_ICONS[currentChallenge.category] || "?"}
            </div>
            <div className="challenge-display__title">{currentChallenge.title}</div>
            <div className="challenge-display__desc">{currentChallenge.description}</div>
            <div className="countdown-ring" style={{ marginTop: "0.8rem" }}>
              <svg viewBox="0 0 64 64">
                <circle className="countdown-ring__bg" cx="32" cy="32" r="28" />
                <circle
                  className="countdown-ring__progress"
                  cx="32"
                  cy="32"
                  r="28"
                  strokeDasharray={176}
                  strokeDashoffset={176 * (1 - countdown / (currentChallenge.duration_seconds || 1))}
                />
              </svg>
              <span className="countdown-ring__label">{countdown}</span>
            </div>
          </div>
        )}

        <div className="timeline-card" style={{ marginTop: "1rem" }}>
          <div className="score-row" style={{ marginTop: 0 }}>
            <strong>Status</strong>
            <span className={`status-pill status-pill--${captureCoach.level}`}>
              {captureCoach.preflightReady ? "Ready to scan" : "Adjust first"}
            </span>
          </div>
          <p className="subtle">{message}</p>
        </div>

        <div className="panel" style={{ marginTop: "1rem", padding: "1rem" }}>
          <div className="score-row" style={{ marginTop: 0 }}>
            <strong>📹 Camera Coach</strong>
            <span className={`status-pill status-pill--${captureCoach.level}`}>
              {captureCoach.headline}
            </span>
          </div>
          {captureCoach.level !== 'good' && (
            <>
              <p className="subtle" style={{ marginTop: "0.6rem" }}>{captureCoach.detail}</p>
              <div className="health-list" style={{ marginTop: "0.8rem" }}>
                {captureCoach.steps.map((item) => (
                  <div className="timeline-card" key={item}>
                    <p className="subtle">{item}</p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {finalState && (
          <div
            className={`result-card ${finalState.authenticated ? "result-card--success" : "result-card--failure"}`}
            style={{ marginTop: "1rem" }}
          >
            <div className="result-card__icon">{finalState.authenticated ? "OK" : "NO"}</div>
            <div className="result-card__score">{formatRatioPercent(finalState.final_score, 1)}</div>
            <p className="subtle">
              {finalState.authenticated ? "Access Granted" : "Access Denied"}
            </p>
            <p className="subtle" style={{ marginTop: "0.6rem" }}>
              This decision score is separate from the capture-quality preview shown during the scan.
            </p>
          </div>
        )}

        <div className="stage-list" style={{ marginTop: "1rem" }}>
          {visibleStageResults.map((result) => {
            const status = finalState
              ? (result.passed ? "passed" : "failed")
              : result.passed
                ? "passed"
                : "pending";

            return (
              <div className={`stage-indicator stage-indicator--${status}`} key={result.stage}>
                <div className="stage-indicator__icon">
                  {status === "passed" ? "OK" : status === "failed" ? "NO" : STAGE_ICONS[result.stage] || "..."}
                </div>
                <div className="stage-indicator__info">
                  <div className="stage-indicator__name">
                    {(result as StageResult).label || result.stage.replaceAll("_", " ")}
                  </div>
                  <div className="stage-indicator__score">
                    Score: {formatRatioPercent(result.score, 1)} / Threshold: {formatRatioPercent(result.threshold, 0)}
                  </div>
                  <div className="stage-indicator__score">{result.message}</div>
                </div>
                <div className={result.passed ? "status-pill status-pill--good" : "status-pill status-pill--warn"}>
                  {formatRatioPercent(result.score, 0)}
                </div>
              </div>
            );
          })}
        </div>
      </article>

      <aside className="panel animate-in-delay">
        <div className="video-shell">
          <video autoPlay muted playsInline ref={videoRef} />
          <canvas hidden ref={canvasRef} />
          <div className={`face-guide ${captureCoach.guideClassName}`} />
        </div>

        <div className="signal-list" style={{ marginTop: "1rem" }}>
          <div className={ready ? "status-pill status-pill--good" : "status-pill status-pill--warn"}>
            {loading ? "Preparing webcam" : ready ? "Live detectors ready" : "Waiting for device access"}
          </div>
          <div className={`status-pill status-pill--${captureCoach.level}`}>
            {captureCoach.preflightReady ? "Face aligned for scan" : "Raise and center the camera"}
          </div>
          {error ? <div className="status-pill status-pill--bad">{error}</div> : null}
        </div>

        <div className="panel" style={{ marginTop: "0.8rem", padding: "1rem" }}>
          <div className="score-row" style={{ marginTop: 0 }}>
            <strong>Do This Now</strong>
            <span className="status-pill status-pill--neutral">
              {running && currentChallenge ? `Prompt ${activeChallenge + 1}/${challenges.length}` : "Pre-scan"}
            </span>
          </div>
          <p className="subtle" style={{ marginTop: "0.6rem" }}>
            {running && currentChallenge
              ? `${currentChallenge.title}: ${currentChallenge.description}`
              : "Align your face before starting the guided scan."}
          </p>
          <div className="health-list" style={{ marginTop: "0.8rem" }}>
            {(running ? challengeSteps : captureCoach.steps).map((item) => (
              <div className="timeline-card" key={item}>
                <p className="subtle">{item}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="panel" style={{ marginTop: "0.8rem", padding: "1rem" }}>
          <strong style={{ fontSize: "0.85rem" }}>Live Scan Feedback</strong>
          <div className="score-row" style={{ marginTop: "0.8rem" }}>
            <span>Capture quality preview</span>
            <strong>{formatScoreOutOfHundred(visibleTelemetry?.quality_score, 1)}</strong>
          </div>
          <p className="subtle" style={{ marginTop: "0.4rem" }}>
            This is camera-quality feedback only. It is not the final access score.
          </p>
          <div className="timeline-row" style={{ marginTop: "0.7rem" }}>
            <span className="subtle">Liveness preview</span>
            <strong>{formatRatioPercent(visibleTelemetry?.liveness_preview_score, 1)}</strong>
          </div>
          <div className="timeline-row">
            <span className="subtle">Challenge progress</span>
            <strong>{formatRatioPercent(visibleTelemetry?.current_challenge_progress, 0)}</strong>
          </div>
          <div className="timeline-row">
            <span className="subtle">Frames processed</span>
            <strong>{visibleTelemetry?.processed_frames ?? 0}</strong>
          </div>
          <div className="timeline-row">
            <span className="subtle">Current prompt score</span>
            <strong>{formatRatioPercent(visibleTelemetry?.current_challenge_score, 1)}</strong>
          </div>
          <div className="signal-list" style={{ marginTop: "0.8rem" }}>
            {telemetryGuidance.length > 0 ? telemetryGuidance.map((item) => (
              <div className="timeline-card" key={item}>
                <p className="subtle">{item}</p>
              </div>
            )) : (
              <div className="timeline-card">
                <p className="subtle">Guidance will appear here during the scan.</p>
              </div>
            )}
          </div>
        </div>

        {challenges.length > 0 && (
          <div className="panel" style={{ marginTop: "0.8rem", padding: "1rem" }}>
            <strong style={{ fontSize: "0.85rem" }}>Challenge Queue</strong>
            <div className="stage-list" style={{ marginTop: "0.6rem", gap: "0.4rem" }}>
              {challengeTelemetry.map((challengeTelemetryItem, index) => (
                <div
                  key={challengeTelemetryItem.id}
                  className={`stage-indicator ${
                    challengeTelemetryItem.status === "completed"
                      ? (challengeTelemetryItem.passed ? "stage-indicator--passed" : "stage-indicator--failed")
                      : challengeTelemetryItem.status === "running"
                        ? "stage-indicator--running"
                        : "stage-indicator--pending"
                  }`}
                  style={{ padding: "0.5rem 0.7rem" }}
                >
                  <div className="stage-indicator__icon" style={{ width: "22px", height: "22px", fontSize: "0.7rem" }}>
                    {challengeTelemetryItem.status === "completed"
                      ? (challengeTelemetryItem.passed ? "OK" : "NO")
                      : challengeTelemetryItem.status === "running"
                        ? "RUN"
                        : CHALLENGE_ICONS[challenges[index]?.category] || "?"}
                  </div>
                  <div className="stage-indicator__info">
                    <div className="stage-indicator__name" style={{ fontSize: "0.8rem" }}>{challengeTelemetryItem.title}</div>
                    <div className="stage-indicator__score">
                      {challengeTelemetryItem.frames_processed} frames / {formatRatioPercent(challengeTelemetryItem.progress, 0)}
                      {typeof challengeTelemetryItem.score === "number"
                        ? ` / ${formatRatioPercent(challengeTelemetryItem.score, 0)}`
                        : ""}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {finalState && finalState.denial_reasons.length > 0 && (
          <div className="panel" style={{ marginTop: "0.8rem", padding: "1rem" }}>
            <strong style={{ fontSize: "0.85rem", color: "var(--warning)" }}>Why Access Was Denied</strong>
            {finalState.denial_reasons.map((reason) => (
              <p key={reason} className="subtle" style={{ fontSize: "0.82rem", marginTop: "0.4rem" }}>{reason}</p>
            ))}
          </div>
        )}

        {finalState && finalState.anomalies.length > 0 && (
          <div className="panel" style={{ marginTop: "0.8rem", padding: "1rem" }}>
            <strong style={{ fontSize: "0.85rem", color: "var(--danger)" }}>Security Flags</strong>
            {finalState.anomalies.map((anomaly) => (
              <p key={anomaly} className="subtle" style={{ fontSize: "0.82rem", marginTop: "0.3rem" }}>{anomaly}</p>
            ))}
          </div>
        )}
      </aside>
    </section>
  );
}
