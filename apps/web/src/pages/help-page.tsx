import { useState } from "react";

const faqs = [
  { q: "What lighting works best?", a: "Use even front lighting. Avoid strong backlight, mixed color temperatures, and harsh shadows across the eyes. Natural daylight from a window in front of you is ideal." },
  { q: "Why am I being asked to remove sunglasses or masks?", a: "The system verifies eye-region geometry, skin texture, and challenge compliance. Occluding that region reduces confidence below acceptance thresholds and triggers denial." },
  { q: "Can I use accessibility-friendly challenges?", a: "Yes. During registration, enable accessibility flags to steer challenge selection away from eye-only or head-turn-heavy prompts. The engine will adapt the sequence accordingly." },
  { q: "What should I do if I changed my appearance?", a: "Minor changes (haircut, glasses) are tolerated due to geometric invariance. Major surgical or long-term facial changes should trigger re-enrollment via your profile page." },
  { q: "Why was my authentication blocked?", a: "Common reasons include: insufficient lighting, face too far/close to camera, failed challenge compliance, or PAD/deepfake detection flags. Check the anomaly list in your result for specific reasons." },
  { q: "How is my biometric data protected?", a: "Templates are encrypted using AES-256-GCM with per-user keys derived via PBKDF2-HMAC-SHA256. Raw images are never stored — only encrypted feature vectors." },
  { q: "What happens after 3 failed attempts?", a: "Your account is temporarily locked for 15 minutes. An admin can unlock it earlier via the admin dashboard." },
  { q: "How many challenge types are there?", a: "38 challenge types across 7 categories: eye (9), mouth (8), head (7), expression (5), distance (1), combined (4), and cognitive (3)." },
];

const tips = [
  { icon: "📸", title: "Camera Position", desc: "Keep your face centered with both eyes visible. The face guide will pulse green when your position is optimal." },
  { icon: "💡", title: "Lighting", desc: "Face a light source. Avoid backlighting. The system measures exposure and will guide you if it's too dark or bright." },
  { icon: "📏", title: "Distance", desc: "Stay 40-60cm from the camera. The face size ratio meter shows whether you're too close or too far." },
  { icon: "🧍", title: "Background", desc: "A plain, non-reflective background reduces false positives. Avoid screens or mirrors behind you." },
  { icon: "⏱", title: "Timing", desc: "Hold still during each capture. Wait for the autofocus indicator before pressing capture. Move naturally during challenges." },
  { icon: "🔄", title: "Re-capture", desc: "If a step is rejected, adjust your position based on the guidance message and try again before the session expires." },
];

export function HelpPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <section className="two-column">
      <article className="panel animate-in">
        <span className="kicker">📖 Help Center</span>
        <h1 style={{ fontSize: "1.8rem", marginTop: "0.8rem" }}>Help & Troubleshooting</h1>
        <p className="lead">
          Tips to get the best results from your webcam during registration and authentication.
        </p>

        <div className="content-grid" style={{ marginTop: "1.5rem", gridTemplateColumns: "repeat(2, 1fr)" }}>
          {tips.map((tip) => (
            <div className="feature-card" key={tip.title} style={{ textAlign: "left", padding: "1.2rem" }}>
              <span style={{ fontSize: "1.5rem" }}>{tip.icon}</span>
              <div className="feature-card__title" style={{ marginTop: "0.5rem", fontSize: "0.95rem" }}>{tip.title}</div>
              <p className="subtle" style={{ fontSize: "0.82rem" }}>{tip.desc}</p>
            </div>
          ))}
        </div>
      </article>

      <aside className="panel animate-in-delay">
        <h2>Frequently Asked Questions</h2>
        <div className="faq-list" style={{ marginTop: "0.8rem" }}>
          {faqs.map((item, i) => (
            <div
              className={`accordion-item ${openFaq === i ? "accordion-item--open" : ""}`}
              key={i}
            >
              <div className="accordion-header" onClick={() => setOpenFaq(openFaq === i ? null : i)}>
                <span>{item.q}</span>
                <span className="accordion-header__icon">▾</span>
              </div>
              <div className="accordion-content">
                <p className="subtle">{item.a}</p>
              </div>
            </div>
          ))}
        </div>
      </aside>
    </section>
  );
}
