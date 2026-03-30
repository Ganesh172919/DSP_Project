import { useEffect, useState } from "react";
import { fetchDashboardMetrics } from "../lib/api";
import type { DashboardMetrics } from "../lib/types";

const fallback: DashboardMetrics = {
  total_authentications: 0,
  success_rate: 0,
  blocked_attacks: 0,
  average_latency_ms: 0,
  active_alerts: 0,
  recent_events: [],
};

export function AdminPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics>(fallback);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    fetchDashboardMetrics().then(setMetrics).catch(() => setMetrics(fallback));
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchDashboardMetrics().then(setMetrics).catch(() => {});
    }, 15000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const successPercent = (metrics.success_rate * 100).toFixed(1);
  const chartData = [0.4, 0.65, 0.55, 0.82, 0.6, 0.74, 0.68, 0.91];
  const attackTypes = (metrics as any).attack_type_counts || {};
  const challengeRates = (metrics as any).challenge_success_rates || {};

  return (
    <section className="animate-in">
      {/* Top metrics */}
      <div className="stats-row" style={{ marginBottom: "1.2rem" }}>
        {[
          { label: "Total Auths", value: metrics.total_authentications, icon: "🔐" },
          { label: "Success Rate", value: `${successPercent}%`, icon: "📈" },
          { label: "Blocked Attacks", value: metrics.blocked_attacks, icon: "🛡" },
          { label: "Avg Latency", value: `${metrics.average_latency_ms.toFixed(0)}ms`, icon: "⚡" },
          { label: "Active Alerts", value: metrics.active_alerts, icon: "🚨" },
        ].map((m) => (
          <div className="metric-card" key={m.label}>
            <span style={{ fontSize: "1.4rem" }}>{m.icon}</span>
            <span className="metric-label">{m.label}</span>
            <strong className="metric-value" style={{ fontSize: "1.8rem" }}>{m.value}</strong>
          </div>
        ))}
      </div>

      <div className="content-grid">
        {/* Success rate donut */}
        <article className="panel">
          <h2>Success Rate</h2>
          <div className="donut-chart" style={{ margin: "1.5rem auto" }}>
            <svg viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" />
              <circle
                cx="60" cy="60" r="50" fill="none"
                stroke="url(#grad)" strokeWidth="10" strokeLinecap="round"
                strokeDasharray={314}
                strokeDashoffset={314 * (1 - metrics.success_rate)}
              />
              <defs>
                <linearGradient id="grad"><stop offset="0%" stopColor="var(--accent-2)" /><stop offset="100%" stopColor="var(--accent)" /></linearGradient>
              </defs>
            </svg>
            <span className="donut-chart__label">{successPercent}%</span>
          </div>
          <p className="subtle" style={{ textAlign: "center" }}>
            {metrics.total_authentications} total · {metrics.blocked_attacks} blocked
          </p>
        </article>

        {/* Latency chart */}
        <article className="panel">
          <h2>Latency Distribution</h2>
          <div className="mini-chart">
            {chartData.map((v, i) => (
              <span key={i} style={{ height: `${v * 100}%` }} title={`${(v * metrics.average_latency_ms / 0.7).toFixed(0)}ms`} />
            ))}
          </div>
          <p className="subtle" style={{ marginTop: "0.5rem", textAlign: "center" }}>
            Average: {metrics.average_latency_ms.toFixed(0)} ms
          </p>
        </article>

        {/* Attack breakdown */}
        <article className="panel">
          <h2>Attack Types Detected</h2>
          {Object.keys(attackTypes).length > 0 ? (
            <div className="health-list" style={{ marginTop: "0.8rem" }}>
              {Object.entries(attackTypes).map(([type, count]) => (
                <div className="timeline-card stage-row" key={type}>
                  <span>{type.replaceAll("_", " ")}</span>
                  <span className="status-pill status-pill--bad">{String(count)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="subtle" style={{ marginTop: "1rem" }}>No attacks detected yet. Run authentication flows to populate.</p>
          )}
        </article>
      </div>

      <div className="glow-line" />

      <div className="two-column">
        {/* Activity feed */}
        <article className="panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2>Activity Feed</h2>
            <button
              className="button button--small"
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              {autoRefresh ? "⏸ Pause" : "▶️ Resume"} Auto-refresh
            </button>
          </div>
          <div className="activity-feed" style={{ marginTop: "0.8rem" }}>
            {(metrics.recent_events.length
              ? metrics.recent_events
              : [{
                  id: "bootstrap",
                  event_type: "system",
                  severity: "info",
                  occurred_at: new Date().toISOString(),
                  message: "No production data yet. Run registration and authentication flows to populate analytics.",
                }]
            ).map((event) => (
              <div className="timeline-card feed-row" key={event.id}>
                <div>
                  <div style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                    <span className={`status-pill status-pill--${event.severity === "critical" ? "bad" : event.severity === "warning" ? "warn" : "good"}`} style={{ fontSize: "0.75rem" }}>
                      {event.severity}
                    </span>
                    <strong style={{ fontSize: "0.85rem" }}>{event.event_type}</strong>
                  </div>
                  <p className="subtle" style={{ fontSize: "0.82rem" }}>{event.message}</p>
                </div>
                <small className="subtle" style={{ whiteSpace: "nowrap" }}>
                  {new Date(event.occurred_at).toLocaleTimeString()}
                </small>
              </div>
            ))}
          </div>
        </article>

        {/* Alert pressure + challenge rates */}
        <article className="panel">
          <h2>System Status</h2>
          <div className="health-list" style={{ marginTop: "0.8rem" }}>
            <div className="timeline-card stage-row">
              <span>Active Alerts</span>
              <span className={`status-pill ${metrics.active_alerts > 0 ? "status-pill--warn" : "status-pill--good"}`}>
                {metrics.active_alerts}
              </span>
            </div>
            <div className="timeline-card">
              <strong>PAD Engine</strong>
              <p className="subtle">Screen replay, photo, and mask detection active</p>
            </div>
            <div className="timeline-card">
              <strong>Deepfake Scanner</strong>
              <p className="subtle">Frequency, boundary, rPPG analysis online</p>
            </div>
            <div className="timeline-card">
              <strong>Challenge Engine</strong>
              <p className="subtle">38 challenge types across 7 categories</p>
            </div>
          </div>

          {Object.keys(challengeRates).length > 0 && (
            <>
              <h3 style={{ marginTop: "1rem", fontSize: "0.95rem" }}>Challenge Success Rates</h3>
              <div className="health-list" style={{ marginTop: "0.5rem" }}>
                {Object.entries(challengeRates).slice(0, 6).map(([cid, rate]) => (
                  <div className="quality-bar" key={cid}>
                    <span className="quality-bar__label">{cid.replaceAll("_", " ")}</span>
                    <div className="quality-bar__track">
                      <div className="quality-bar__fill quality-bar__fill--good" style={{ width: `${Number(rate) * 100}%` }} />
                    </div>
                    <span className="quality-bar__value">{(Number(rate) * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </article>
      </div>
    </section>
  );
}
