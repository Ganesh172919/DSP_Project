import { useMemo, useState } from "react";
import { completeRegistration, startRegistration, submitRegistrationFrame } from "../lib/api";
import { useBiometricCapture } from "../lib/use-biometric-capture";

const registrationSteps = [
  { id: "front", label: "Front", icon: "😐", hint: "Look straight at the camera" },
  { id: "left", label: "Left", icon: "👈", hint: "Turn your head slightly left" },
  { id: "right", label: "Right", icon: "👉", hint: "Turn your head slightly right" },
  { id: "up", label: "Up", icon: "👆", hint: "Tilt your head slightly upward" },
  { id: "down", label: "Down", icon: "👇", hint: "Tilt your head slightly downward" },
  { id: "smile", label: "Smile", icon: "😊", hint: "Give a natural, wide smile" },
  { id: "frown", label: "Frown", icon: "😠", hint: "Furrow your brows as if concentrating" },
  { id: "brow_raise", label: "Brows Up", icon: "😮", hint: "Raise both eyebrows high" },
  { id: "squint", label: "Squint", icon: "😑", hint: "Narrow both eyes without closing" },
  { id: "mouth_open", label: "Mouth Open", icon: "😲", hint: "Open your mouth wide" },
];

export function RegisterPage() {
  const { videoRef, canvasRef, ready, error, loading, snapshot, captureSnapshot } = useBiometricCapture();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    accessibility_eye_only: false,
    accessibility_no_head_turns: false,
  });
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [qualityScore, setQualityScore] = useState<number | null>(null);
  const [guidance, setGuidance] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Create a profile, then capture each required enrollment pose.");
  const [finalResult, setFinalResult] = useState<{ quality: number; security: number; steps: number } | null>(null);

  const canStart = useMemo(() => form.full_name && form.email && form.password, [form]);
  const currentStep = registrationSteps[activeStep];
  const allCaptured = activeStep >= registrationSteps.length - 1 && completedSteps.size >= registrationSteps.length;

  const faceMetrics = snapshot.client_metrics;
  const qualityBars = [
    { label: "Face Size", value: Math.min(Number(faceMetrics.face_size_ratio || 0) * 500, 100), unit: "%" },
    { label: "Sharpness", value: Math.abs(Number(faceMetrics.roll || 0)) < 10 ? 85 : 60, unit: "" },
    { label: "Position", value: faceMetrics.face_present ? 90 : 10, unit: "" },
    { label: "Lighting", value: faceMetrics.face_present ? 80 : 30, unit: "" },
  ];

  async function handleStartRegistration() {
    if (!canStart) { setMessage("Please fill out your name, email, and password first."); return; }
    setBusy(true);
    try {
      const response = await startRegistration({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        accessibility_profile: {
          eye_only: form.accessibility_eye_only,
          no_head_turns: form.accessibility_no_head_turns,
        },
      });
      setSessionId(response.session_id);
      setMessage("Enrollment session ready. Capture each step when the face guide is stable.");
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Unable to start registration");
    } finally {
      setBusy(false);
    }
  }

  async function handleCaptureStep() {
    if (!sessionId) { setMessage("Start the registration session before capturing."); return; }
    setBusy(true);
    try {
      const payload = captureSnapshot();
      const response = await submitRegistrationFrame(sessionId, {
        step: currentStep.id,
        frame_b64: payload.frame_b64,
        landmarks: payload.landmarks,
        hand_landmarks: payload.hand_landmarks,
        client_metrics: payload.client_metrics,
        captured_at: new Date().toISOString(),
      });
      setQualityScore(response.quality_score);
      setGuidance(response.guidance);
      if (response.accepted) {
        const newCompleted = new Set(completedSteps);
        newCompleted.add(currentStep.id);
        setCompletedSteps(newCompleted);
        if (activeStep < registrationSteps.length - 1) {
          setActiveStep((c) => c + 1);
          setMessage(`✅ Captured ${currentStep.label}. Move to the next pose.`);
        } else {
          setMessage("All captures submitted! Finalize enrollment to encrypt and store the template.");
        }
      } else {
        setMessage(`⚠️ Capture rejected: ${response.guidance.join(". ")}`);
      }
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Capture failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleFinalizeRegistration() {
    if (!sessionId) return;
    setBusy(true);
    try {
      const response = await completeRegistration(sessionId);
      setFinalResult({
        quality: response.quality_score,
        security: response.security_score,
        steps: (response as any).steps_completed || completedSteps.size,
      });
      setMessage(`🎉 Registration complete!`);
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : "Unable to finalize registration");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="two-column">
      <article className="panel animate-in">
        <span className="kicker">📸 Enrollment Wizard</span>
        <h1 style={{ fontSize: "1.8rem", marginTop: "0.8rem" }}>Register Biometric Template</h1>
        <p className="lead">
          Capture profile-rich face geometry, expression dynamics, and liveness-ready baseline metrics.
        </p>

        {/* Form */}
        <div className="field-grid" style={{ marginTop: "1rem" }}>
          <label className="field">
            <span>Full name</span>
            <input placeholder="John Doe" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          </label>
          <label className="field">
            <span>Email</span>
            <input placeholder="john@example.com" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" placeholder="Min 8 characters" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </label>
        </div>

        {/* Buttons */}
        <div className="button-row">
          <button className="button button--primary" disabled={busy || !!sessionId} onClick={handleStartRegistration}>
            {busy && !sessionId ? "⏳ Starting..." : "⚡ Start Enrollment"}
          </button>
          <button className="button" disabled={busy || !sessionId || allCaptured} onClick={handleCaptureStep}>
            📸 Capture {currentStep?.label}
          </button>
          <button className="button" disabled={busy || !sessionId || !allCaptured} onClick={handleFinalizeRegistration}>
            🔒 Finalize
          </button>
        </div>

        {/* Step indicators */}
        <div className="stepper" style={{ marginTop: "1rem" }}>
          {registrationSteps.map((step, i) => (
            <span
              key={step.id}
              className={`step-pill ${i === activeStep ? "step-pill--active" : ""} ${completedSteps.has(step.id) ? "step-pill--done" : ""}`}
            >
              {completedSteps.has(step.id) ? "✓" : step.icon} {step.label}
            </span>
          ))}
        </div>

        {/* Current step hint */}
        {sessionId && currentStep && !allCaptured && (
          <div className="challenge-display" style={{ marginTop: "1rem", padding: "1.2rem" }}>
            <div className="challenge-display__icon">{currentStep.icon}</div>
            <div className="challenge-display__title">{currentStep.label}</div>
            <div className="challenge-display__desc">{currentStep.hint}</div>
          </div>
        )}

        {/* Status */}
        <div className="timeline-card" style={{ marginTop: "1rem" }}>
          <strong>Status</strong>
          <p className="subtle">{message}</p>
          {typeof qualityScore === "number" && (
            <>
              <div className="score-row" style={{ marginTop: "0.6rem" }}>
                <span>Registration quality</span>
                <strong>{qualityScore.toFixed(1)}/100</strong>
              </div>
              <div className="score-meter">
                <span style={{ width: `${Math.min(qualityScore, 100)}%` }} />
              </div>
            </>
          )}
        </div>

        {/* Final result */}
        {finalResult && (
          <div className="result-card result-card--success" style={{ marginTop: "1rem" }}>
            <div className="result-card__icon">🎉</div>
            <div className="result-card__score">{finalResult.security.toFixed(0)}/100</div>
            <p className="subtle">Security Score · {finalResult.steps} steps · Quality {finalResult.quality.toFixed(1)}</p>
          </div>
        )}

        {/* Guidance */}
        <div className="health-list" style={{ marginTop: "1rem" }}>
          {(guidance.length ? guidance : ["Lighting, face position, and sharpness guidance will appear here."]).map((item) => (
            <div className="timeline-card" key={item}>{item}</div>
          ))}
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
            {loading ? "⏳ Loading camera..." : ready ? "Camera and detectors ready" : "Waiting for access"}
          </div>
          {error ? <div className="status-pill status-pill--bad">❌ {error}</div> : null}
        </div>

        {/* Quality meters */}
        <div className="quality-bars" style={{ marginTop: "1rem" }}>
          {qualityBars.map((bar) => {
            const level = bar.value >= 70 ? "good" : bar.value >= 40 ? "warn" : "bad";
            return (
              <div className="quality-bar" key={bar.label}>
                <span className="quality-bar__label">{bar.label}</span>
                <div className="quality-bar__track">
                  <div className={`quality-bar__fill quality-bar__fill--${level}`} style={{ width: `${bar.value}%` }} />
                </div>
                <span className="quality-bar__value">{bar.value.toFixed(0)}{bar.unit}</span>
              </div>
            );
          })}
        </div>

        {/* Live metrics */}
        <div className="signal-list" style={{ marginTop: "0.8rem" }}>
          <div className="timeline-card">
            <strong>Live Hint</strong>
            <p className="subtle">{String(faceMetrics.quality_hint ?? "No signal yet")}</p>
          </div>
          <div className="timeline-card">
            <strong>Head Pose</strong>
            <p className="subtle">
              Yaw {String(faceMetrics.yaw ?? 0)}° · Pitch {String(faceMetrics.pitch ?? 0)}° · Roll {String(faceMetrics.roll ?? 0)}°
            </p>
          </div>
        </div>
      </aside>
    </section>
  );
}
