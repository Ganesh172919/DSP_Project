import { Link } from "react-router-dom";

const defenseStack = [
  { icon: "👁", title: "Challenge-Response Liveness", desc: "Randomised eye, head, expression, and hand interactions with 38 challenge types across 7 categories" },
  { icon: "🛡", title: "Passive PAD", desc: "Screen replay, printed photo, and 3D mask detection using FFT moiré analysis, LBP texture, and specular reflection" },
  { icon: "🧬", title: "Granular Biometrics", desc: "73+ morphological features across eyes, nose, lips, eyebrows, jawline, and face geometry" },
  { icon: "🔬", title: "Deepfake Detection", desc: "Frequency-domain analysis, face boundary blending, temporal consistency, rPPG pulse signal verification" },
  { icon: "🔒", title: "Encrypted Templates", desc: "AES-256-GCM per-user key derivation with PKCS PBKDF2-HMAC-SHA256 and integrity hashing" },
  { icon: "📊", title: "Auditable Decisions", desc: "Per-stage scores, weighted fusion, anomaly flags, and complete decision trace for forensic review" },
];

const stats = [
  { label: "Defense Layers", value: "7", suffix: "" },
  { label: "Challenge Types", value: "38", suffix: "" },
  { label: "Biometric Features", value: "73", suffix: "+" },
  { label: "Pipeline Target", value: "<3", suffix: "s" },
];

const attacks = [
  { name: "Screen Replay", icon: "📱", desc: "Moiré detection, color temperature, pixel grid" },
  { name: "Printed Photo", icon: "🖼", desc: "Paper texture, halftone, gamut analysis" },
  { name: "3D Mask", icon: "🎭", desc: "LBP texture, specular reflection, boundary" },
  { name: "Deepfake", icon: "🤖", desc: "Frequency spectrum, boundary blend, rPPG" },
  { name: "Replay Video", icon: "📹", desc: "Temporal jitter, brightness stability" },
  { name: "Morphed Image", icon: "🔀", desc: "Feature consistency, embedding divergence" },
];

const steps = [
  { num: "01", title: "Enrollment", desc: "Multi-angle face capture with 10-step quality-gated registration and real-time guidance", icon: "📸" },
  { num: "02", title: "Template Protection", desc: "AES-256-GCM encrypted biometric templates with per-user key derivation and integrity verification", icon: "🔐" },
  { num: "03", title: "Verification", desc: "7-stage cascade: detection → PAD → recognition → features → liveness → deepfake → decision", icon: "✅" },
];

export function LandingPage() {
  return (
    <>
      {/* ── Hero ── */}
      <section className="hero-grid animate-in">
        <article className="panel panel--hero">
          <span className="kicker">⚡ RGB camera only · PAD-first verification</span>
          <h1 className="page-title">Face authentication that assumes the attacker already knows the face.</h1>
          <p className="lead">
            DeepShield Guardian combines browser-side landmarking, server-side biometric template protection,
            challenge-response liveness, and multi-modal deepfake risk scoring into a deployable full-stack
            security gateway.
          </p>
          <div className="button-row">
            <Link className="button button--primary" to="/register">⚡ Start Enrollment</Link>
            <Link className="button" to="/authenticate">🔍 Run Authentication</Link>
          </div>
        </article>

        <aside className="panel" style={{ display: "grid", gap: "0.8rem", alignContent: "center" }}>
          {stats.map((s, i) => (
            <div className="metric-card" key={s.label} style={{ animationDelay: `${i * 0.1}s` }}>
              <span className="metric-label">{s.label}</span>
              <strong className="metric-value">{s.value}{s.suffix}</strong>
            </div>
          ))}
        </aside>
      </section>

      <div className="glow-line" />

      {/* ── Defense Stack ── */}
      <section className="animate-in-delay">
        <h2 className="section-title" style={{ textAlign: "center", marginBottom: "1.2rem" }}>Defense Stack</h2>
        <div className="content-grid">
          {defenseStack.map((item) => (
            <div className="feature-card" key={item.title}>
              <span className="feature-card__icon">{item.icon}</span>
              <div className="feature-card__title">{item.title}</div>
              <p className="subtle">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="glow-line" />

      {/* ── How It Works ── */}
      <section className="animate-in-delay-2">
        <h2 className="section-title" style={{ textAlign: "center", marginBottom: "1.2rem" }}>How It Works</h2>
        <div className="content-grid">
          {steps.map((step) => (
            <div className="panel" key={step.num} style={{ textAlign: "center", padding: "2rem 1.5rem" }}>
              <span style={{ fontSize: "2.5rem" }}>{step.icon}</span>
              <div style={{ marginTop: "0.8rem" }}>
                <span className="kicker--purple kicker">{step.num}</span>
              </div>
              <h3 style={{ marginTop: "0.8rem" }}>{step.title}</h3>
              <p className="subtle">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="glow-line" />

      {/* ── What We Block ── */}
      <section>
        <h2 className="section-title" style={{ textAlign: "center", marginBottom: "1.2rem" }}>Attack Types We Detect</h2>
        <div className="content-grid">
          {attacks.map((attack) => (
            <div className="timeline-card" key={attack.name} style={{ textAlign: "center" }}>
              <span style={{ fontSize: "1.8rem", display: "block", marginBottom: "0.5rem" }}>{attack.icon}</span>
              <strong>{attack.name}</strong>
              <p className="subtle" style={{ fontSize: "0.82rem" }}>{attack.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="glow-line" />

      {/* ── Built for Real ── */}
      <section className="panel" style={{ textAlign: "center", padding: "2.5rem" }}>
        <h2 className="section-title">Built for Real Deployments</h2>
        <p className="lead" style={{ margin: "0 auto 1.5rem" }}>
          Ships with FastAPI microservices, Docker Compose, PostgreSQL, Redis, Kubernetes manifests,
          and thesis-style documentation. Serves as both an engineering deliverable and an academic baseline.
        </p>
        <div className="button-row" style={{ justifyContent: "center" }}>
          <Link className="button button--primary" to="/register">Get Started</Link>
          <Link className="button" to="/help">View Documentation</Link>
        </div>
      </section>
    </>
  );
}
