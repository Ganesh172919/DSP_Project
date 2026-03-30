import { useState } from "react";
import { fetchProfile } from "../lib/api";

interface ProfileData {
  full_name: string;
  email: string;
  registration_completed: boolean;
  template_quality_score: number;
  security_score: number;
  re_enrollment_due?: string;
  recent_attempts: Array<{
    id: string;
    status: string;
    final_score: number;
    created_at: string;
  }>;
}

export function ProfilePage() {
  const [email, setEmail] = useState("");
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function loadProfile() {
    setLoading(true);
    try {
      const result = await fetchProfile(email);
      setProfile(result as ProfileData);
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load profile");
    } finally {
      setLoading(false);
    }
  }

  const gaugeValue = profile ? Math.min(profile.security_score, 100) : 0;
  const gaugeColor = gaugeValue >= 80 ? "var(--success)" : gaugeValue >= 50 ? "var(--warning)" : "var(--danger)";
  const circumference = Math.PI * 70; // half circle
  const offset = circumference * (1 - gaugeValue / 100);

  return (
    <section className="two-column">
      <article className="panel animate-in">
        <span className="kicker">👤 User Profile</span>
        <h1 style={{ fontSize: "1.8rem", marginTop: "0.8rem" }}>Your Biometric Profile</h1>
        <p className="lead">Review registration status, template quality, and recent authentication history.</p>

        <div className="field-grid" style={{ marginTop: "1rem" }}>
          <label className="field">
            <span>Email</span>
            <input placeholder="john@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
        </div>
        <div className="button-row">
          <button className="button button--primary" disabled={loading || !email} onClick={loadProfile}>
            {loading ? "⏳ Loading..." : "🔎 Load Profile"}
          </button>
        </div>

        {error && <div className="status-pill status-pill--bad" style={{ marginTop: "0.8rem" }}>❌ {error}</div>}

        {profile && (
          <>
            {/* Security gauge */}
            <div className="security-gauge" style={{ marginTop: "1.5rem" }}>
              <svg viewBox="0 0 160 90">
                <path d="M 10 80 A 70 70 0 0 1 150 80" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" strokeLinecap="round" />
                <path
                  d="M 10 80 A 70 70 0 0 1 150 80" fill="none"
                  stroke={gaugeColor} strokeWidth="10" strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={offset}
                  style={{ transition: "stroke-dashoffset 1s ease-out" }}
                />
              </svg>
              <span className="security-gauge__label" style={{ color: gaugeColor }}>
                {gaugeValue.toFixed(0)}
              </span>
            </div>
            <p className="subtle" style={{ textAlign: "center" }}>Security Score</p>

            {/* Profile info */}
            <div className="health-list" style={{ marginTop: "1.2rem" }}>
              <div className="timeline-card stage-row">
                <div>
                  <strong>{profile.full_name}</strong>
                  <p className="subtle">{profile.email}</p>
                </div>
                <span className={`status-pill ${profile.registration_completed ? "status-pill--good" : "status-pill--warn"}`}>
                  {profile.registration_completed ? "✓ Enrolled" : "⏳ Pending"}
                </span>
              </div>

              <div className="quality-bar">
                <span className="quality-bar__label">Quality</span>
                <div className="quality-bar__track">
                  <div
                    className={`quality-bar__fill quality-bar__fill--${profile.template_quality_score >= 70 ? "good" : profile.template_quality_score >= 40 ? "warn" : "bad"}`}
                    style={{ width: `${Math.min(profile.template_quality_score, 100)}%` }}
                  />
                </div>
                <span className="quality-bar__value">{profile.template_quality_score.toFixed(1)}</span>
              </div>

              <div className="quality-bar">
                <span className="quality-bar__label">Security</span>
                <div className="quality-bar__track">
                  <div
                    className={`quality-bar__fill quality-bar__fill--${profile.security_score >= 70 ? "good" : profile.security_score >= 40 ? "warn" : "bad"}`}
                    style={{ width: `${Math.min(profile.security_score, 100)}%` }}
                  />
                </div>
                <span className="quality-bar__value">{profile.security_score.toFixed(1)}</span>
              </div>

              {profile.re_enrollment_due && (
                <div className="timeline-card">
                  <strong>Re-enrollment Due</strong>
                  <p className="subtle">{new Date(profile.re_enrollment_due).toLocaleDateString()}</p>
                </div>
              )}
            </div>
          </>
        )}
      </article>

      <aside className="panel animate-in-delay">
        <h2>Authentication History</h2>
        <div className="activity-feed" style={{ marginTop: "0.8rem" }}>
          {(profile?.recent_attempts?.length
            ? profile.recent_attempts
            : [{ id: "placeholder", status: "pending", final_score: 0, created_at: new Date().toISOString() }]
          ).map((attempt) => (
            <div className="timeline-card" key={attempt.id}>
              <div className="stage-row">
                <div>
                  <span className={`status-pill ${
                    attempt.status === "approved" ? "status-pill--good" :
                    attempt.status === "denied" ? "status-pill--bad" :
                    "status-pill--warn"
                  }`}>
                    {attempt.status === "approved" ? "✓ Approved" : attempt.status === "denied" ? "✗ Denied" : "⏳ " + attempt.status}
                  </span>
                  <p className="subtle" style={{ marginTop: "0.3rem" }}>Score: {attempt.final_score.toFixed(2)}</p>
                </div>
                <small className="subtle">{new Date(attempt.created_at).toLocaleString()}</small>
              </div>
            </div>
          ))}
        </div>

        {!profile && (
          <div style={{ marginTop: "2rem", textAlign: "center" }}>
            <span style={{ fontSize: "3rem", display: "block", marginBottom: "0.8rem" }}>👤</span>
            <p className="subtle">Enter your email and load your profile to see authentication history.</p>
          </div>
        )}
      </aside>
    </section>
  );
}
