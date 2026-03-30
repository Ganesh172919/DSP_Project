import { useCallback, useEffect, useMemo, useState } from "react";
import {
  completeAuthentication,
  startAuthentication,
  submitAuthenticationFrame,
} from "../lib/api";
import type { AuthenticationStateResponse, ChallengeDefinition, StageResult } from "../lib/types";
import { useBiometricCapture } from "../lib/use-biometric-capture";

const CHALLENGE_ICONS: Record<string, string> = {
  eye: "👁", mouth: "👄", head: "🔄", expression: "😊",
  distance: "↔️", combined: "🔗", cognitive: "🖐",
};

const STAGE_ICONS: Record<string, string> = {
  face_detection: "🔍", presentation_attack_detection: "🛡",
  recognition: "🧬", feature_verification: "📐",
  liveness: "💓", deepfake_scan: "🔬",
};

export function AuthenticatePage() {
  const { videoRef, canvasRef, ready, loading, error, captureSnapshot, snapshot } = useBiometricCapture();
  const [email, setEmail] = useState("");
  const [attemptId, setAttemptId] = useState<string | null>(null);
  const [challenges, setChallenges] = useState<ChallengeDefinition[]>([]);
  const [activeChallenge, setActiveChallenge] = useState(0);
  const [stageResults, setStageResults] = useState<StageResult[]>([]);
  const [finalState, setFinalState] = useState<AuthenticationStateResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [running, setRunning] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [message, setMessage] = useState("Enter your email, then run the live challenge sequence.");
  const [attemptsInfo, setAttemptsInfo] = useState({ number: 0, remaining: 3 });

  const currentChallenge = useMemo(() => challenges[activeChallenge], [activeChallenge, challenges]);

  async function handleStartAuthentication() {
    setBusy(true);
    setFinalState(null);
    setStageResults([]);
    try {
      const response = await startAuthentication({ email });
      setAttemptId(response.attempt_id);
      setChallenges(response.challenges);
      setActiveChallenge(0);
      setAttemptsInfo({
        number: (response as any).attempt_number || 1,
        remaining: (response as any).max_attempts || 3,
      });
      setMessage("Challenge sequence issued. Press 'Begin Live Scan' when ready.");
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Unable to start authentication");
    } finally {
      setBusy(false);
    }
  }

  async function runChallengeSequence() {
    if (!attemptId || !challenges.length) {
      setMessage("Start an authentication attempt first.");
      return;
    }

    setBusy(true);
    setRunning(true);
    setMessage("Running live challenge sequence. Follow the prompts.");
    try {
      for (let i = 0; i < challenges.length; i++) {
        const challenge = challenges[i];
        setActiveChallenge(i);
        setCountdown(challenge.duration_seconds);

        const loops = Math.max(3, challenge.duration_seconds);
        for (let f = 0; f < loops; f++) {
          setCountdown(Math.max(0, challenge.duration_seconds - f));
          const payload = captureSnapshot();
          const response = await submitAuthenticationFrame(attemptId, {
            step: "authentication_live_frame",
            challenge_id: challenge.id,
            frame_b64: payload.frame_b64,
            landmarks: payload.landmarks,
            hand_landmarks: payload.hand_landmarks,
            client_metrics: payload.client_metrics,
            captured_at: new Date().toISOString(),
          });
          setStageResults(response.stage_results);
          await new Promise((r) => setTimeout(r, 800));
        }
      }

      const decision = await completeAuthentication(attemptId);
      setFinalState(decision);
      setStageResults(decision.stage_results);
      setAttemptsInfo((prev) => ({
        ...prev,
        remaining: (decision as any).attempts_remaining ?? prev.remaining,
      }));
      setMessage(
        decision.authenticated
          ? `✅ Authentication successful!`
          : `❌ Authentication denied. ${decision.anomalies?.join(". ") || "Stage thresholds not met."}`
      );
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Authentication sequence failed");
    } finally {
      setBusy(false);
      setRunning(false);
      setCountdown(0);
    }
  }

  function getStageStatus(result: StageResult) {
    if (running && !finalState) return "running";
    return result.passed ? "passed" : "failed";
  }

  return (
    <section className="two-column">
      <article className="panel animate-in">
        <span className="kicker">🔍 Verification Cascade</span>
        <h1 style={{ fontSize: "1.8rem", marginTop: "0.8rem" }}>Authenticate</h1>
        <p className="lead">
          The server evaluates passive PAD, geometric matching, challenge compliance,
          and deepfake risk before returning a decision.
        </p>

        <div className="field-grid" style={{ marginTop: "1rem" }}>
          <label className="field">
            <span>Registered email</span>
            <input placeholder="john@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
        </div>

        <div className="button-row">
          <button className="button button--primary" disabled={busy || !email} onClick={handleStartAuthentication}>
            ⚡ Start Authentication
          </button>
          <button className="button" disabled={busy || !attemptId || !ready || running} onClick={runChallengeSequence}>
            💓 Begin Live Scan
          </button>
        </div>

        {attemptsInfo.number > 0 && (
          <div style={{ marginTop: "0.8rem", display: "flex", gap: "0.5rem" }}>
            <span className="kicker">Attempt #{attemptsInfo.number}</span>
            <span className={`kicker ${attemptsInfo.remaining <= 1 ? "kicker--danger" : "kicker--purple"}`}>
              {attemptsInfo.remaining} remaining
            </span>
          </div>
        )}

        {/* Active challenge display */}
        {running && currentChallenge && (
          <div className="challenge-display" style={{ marginTop: "1rem" }}>
            <div className="challenge-display__icon">
              {CHALLENGE_ICONS[currentChallenge.category] || "❓"}
            </div>
            <div className="challenge-display__title">{currentChallenge.title}</div>
            <div className="challenge-display__desc">{currentChallenge.description}</div>
            <div className="countdown-ring" style={{ marginTop: "0.8rem" }}>
              <svg viewBox="0 0 64 64">
                <circle className="countdown-ring__bg" cx="32" cy="32" r="28" />
                <circle
                  className="countdown-ring__progress"
                  cx="32" cy="32" r="28"
                  strokeDasharray={176}
                  strokeDashoffset={176 * (1 - countdown / (currentChallenge.duration_seconds || 1))}
                />
              </svg>
              <span className="countdown-ring__label">{countdown}</span>
            </div>
          </div>
        )}

        {/* Status */}
        <div className="timeline-card" style={{ marginTop: "1rem" }}>
          <strong>Status</strong>
          <p className="subtle">{message}</p>
        </div>

        {/* Final result */}
        {finalState && (
          <div className={`result-card ${finalState.authenticated ? "result-card--success" : "result-card--failure"}`} style={{ marginTop: "1rem" }}>
            <div className="result-card__icon">{finalState.authenticated ? "✅" : "🚫"}</div>
            <div className="result-card__score">{finalState.final_score?.toFixed(2) ?? "--"}</div>
            <p className="subtle">{finalState.authenticated ? "Access Granted" : "Access Denied"}</p>
          </div>
        )}

        {/* Stage results */}
        <div className="stage-list" style={{ marginTop: "1rem" }}>
          {(stageResults.length ?
            stageResults :
            [{ stage: "face_detection", score: Number(snapshot.client_metrics.face_size_ratio ?? 0), passed: Boolean(snapshot.client_metrics.face_present), message: String(snapshot.client_metrics.quality_hint ?? "Awaiting live stream"), label: "Face Detection", weight: 0.1, threshold: 0.55 }]
          ).map((result) => {
            const status = finalState ? (result.passed ? "passed" : "failed") : "pending";
            return (
              <div className={`stage-indicator stage-indicator--${status}`} key={result.stage}>
                <div className="stage-indicator__icon">
                  {status === "passed" ? "✓" : status === "failed" ? "✗" : STAGE_ICONS[result.stage] || "⏳"}
                </div>
                <div className="stage-indicator__info">
                  <div className="stage-indicator__name">
                    {(result as any).label || result.stage.replaceAll("_", " ")}
                  </div>
                  <div className="stage-indicator__score">
                    Score: {result.score.toFixed(3)} · Threshold: {(result as any).threshold?.toFixed(2) ?? "—"}
                  </div>
                </div>
                <div className={result.passed ? "status-pill status-pill--good" : "status-pill status-pill--warn"}>
                  {result.score.toFixed(2)}
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
          <div className="face-guide" />
        </div>

        <div className="signal-list" style={{ marginTop: "1rem" }}>
          <div className={ready ? "status-pill status-pill--good" : "status-pill status-pill--warn"}>
            {loading ? "⏳ Preparing webcam" : ready ? "Live detectors ready" : "Waiting for device access"}
          </div>
          {error ? <div className="status-pill status-pill--bad">❌ {error}</div> : null}
        </div>

        {/* Challenge queue */}
        {challenges.length > 0 && (
          <div className="panel" style={{ marginTop: "0.8rem", padding: "1rem" }}>
            <strong style={{ fontSize: "0.85rem" }}>Challenge Queue</strong>
            <div className="stage-list" style={{ marginTop: "0.6rem", gap: "0.4rem" }}>
              {challenges.map((c, i) => (
                <div
                  key={c.id}
                  className={`stage-indicator ${i < activeChallenge ? "stage-indicator--passed" : i === activeChallenge && running ? "stage-indicator--running" : "stage-indicator--pending"}`}
                  style={{ padding: "0.5rem 0.7rem" }}
                >
                  <div className="stage-indicator__icon" style={{ width: "22px", height: "22px", fontSize: "0.7rem" }}>
                    {i < activeChallenge ? "✓" : i === activeChallenge && running ? "⟳" : CHALLENGE_ICONS[c.category] || "?"}
                  </div>
                  <div className="stage-indicator__info">
                    <div className="stage-indicator__name" style={{ fontSize: "0.8rem" }}>{c.title}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Anomalies */}
        {finalState && finalState.anomalies.length > 0 && (
          <div className="panel" style={{ marginTop: "0.8rem", padding: "1rem" }}>
            <strong style={{ fontSize: "0.85rem", color: "var(--danger)" }}>⚠️ Anomalies</strong>
            {finalState.anomalies.map((a, i) => (
              <p key={i} className="subtle" style={{ fontSize: "0.82rem", marginTop: "0.3rem" }}>• {a}</p>
            ))}
          </div>
        )}
      </aside>
    </section>
  );
}
