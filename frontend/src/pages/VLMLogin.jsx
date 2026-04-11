import React, { useState, useRef, useCallback, useEffect } from 'react';
import client from '../api/client';

const BrainIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="icon-sm">
    <path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z" />
    <path d="M10 21h4M12 17v4" />
  </svg>
);

/**
 * VLMLogin — VLM-enhanced authentication page.
 *
 * 3-step flow: username → record 5s video → results with VLM reasoning.
 * Shows full AI analysis including VLM natural language explanation.
 */
export default function VLMLogin() {
  const [step, setStep] = useState(1);
  const [username, setUsername] = useState('');
  const [videoBlob, setVideoBlob] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Camera
  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [recording, setRecording] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [recordTime, setRecordTime] = useState(5);
  const RECORD_DURATION = 5;

  // Step 1 → 2
  const handleNext = useCallback(async () => {
    if (!username.trim()) { setError('Please enter your username'); return; }
    setError('');
    setStep(2);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setCameraReady(true);
    } catch {
      setError('Camera access denied.');
      setStep(1);
    }
  }, [username]);

  // Countdown
  const handleStartRecording = useCallback(() => setCountdown(3), []);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => {
      if (countdown === 1) { beginRecording(); setCountdown(0); }
      else setCountdown(countdown - 1);
    }, 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  const beginRecording = useCallback(() => {
    if (!streamRef.current) return;
    chunksRef.current = [];
    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9' : 'video/webm';
    const recorder = new MediaRecorder(streamRef.current, { mimeType });
    recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: mimeType });
      setVideoBlob(blob);
      setRecording(false);
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
      setStep(3);
    };
    mediaRecorderRef.current = recorder;
    recorder.start(100);
    setRecording(true);
    setRecordTime(RECORD_DURATION);
    setTimeout(() => { if (recorder.state === 'recording') recorder.stop(); }, RECORD_DURATION * 1000);
  }, []);

  useEffect(() => {
    if (!recording) return;
    const timer = setInterval(() => {
      setRecordTime(prev => { if (prev <= 0.1) { clearInterval(timer); return 0; } return prev - 0.1; });
    }, 100);
    return () => clearInterval(timer);
  }, [recording]);

  // Submit
  const handleSubmit = useCallback(async () => {
    if (!videoBlob) { setError('No video recorded'); return; }
    setError('');
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('video', videoBlob, 'auth_video.webm');
      const resp = await client.post('/vlm/authenticate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000, // 5 min — VLM can be slow on CPU
      });
      setResult(resp.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed');
    }
    setLoading(false);
  }, [username, videoBlob]);

  // Auto-submit
  useEffect(() => {
    if (step === 3 && videoBlob && !result && !loading) handleSubmit();
  }, [step, videoBlob, result, loading, handleSubmit]);

  // Cleanup
  useEffect(() => () => {
    if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
  }, []);

  const handleReset = () => {
    setStep(1); setUsername(''); setVideoBlob(null); setResult(null);
    setError(''); setLoading(false); setCameraReady(false); setRecording(false);
    if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
  };

  const progress = ((RECORD_DURATION - recordTime) / RECORD_DURATION) * 100;

  return (
    <div className="page">
      <div className="card login-card vlm-card">
        {/* Header */}
        <div className="card-header">
          <div className="vlm-badge">
            <span className="vlm-badge-icon">🧠</span>
            <span>VLM Enhanced</span>
          </div>
          <div className="card-icon"><BrainIcon /></div>
          <h1>VLM Authenticate</h1>
          <p className="card-subtitle">AI-powered verification with natural language reasoning</p>
        </div>

        {/* Stepper */}
        <div className="stepper">
          {['Username', 'Record (5s)', 'AI Analysis'].map((label, i) => (
            <div key={i} className={`step-dot ${step > i + 1 ? 'completed' : ''} ${step === i + 1 ? 'active' : ''}`}>
              <div className="dot">{step > i + 1 ? '✓' : i + 1}</div>
              <span className="step-label">{label}</span>
            </div>
          ))}
        </div>

        {error && <div className="alert alert-error"><span>⚠️</span> {error}</div>}

        {/* Step 1: Username */}
        {step === 1 && (
          <div className="step-content fade-in">
            <div className="form-group">
              <label htmlFor="vlm-login-username">Username</label>
              <input id="vlm-login-username" type="text" className="form-input"
                value={username} onChange={e => setUsername(e.target.value)}
                placeholder="Enter your registered username"
                onKeyDown={e => e.key === 'Enter' && handleNext()} autoFocus />
            </div>
            <div className="vlm-info-box">
              <h4>🧠 Hybrid Authentication</h4>
              <p>Your video will be analyzed by both traditional ML models and a Vision Language Model
                for comprehensive face verification with explainable reasoning.</p>
            </div>
            <button className="btn btn-primary" onClick={handleNext} disabled={!username.trim()}>
              Next →
            </button>
          </div>
        )}

        {/* Step 2: Record */}
        {step === 2 && (
          <div className="step-content fade-in">
            <div className="video-instructions">
              <p>Look directly at the camera and keep your face visible.</p>
              <p className="video-hint">Recording 5 seconds for comprehensive VLM + traditional analysis.</p>
            </div>
            <div className="camera-container active">
              <video ref={videoRef} autoPlay playsInline muted className="camera-video" />
              {countdown > 0 && (
                <div className="countdown-overlay">
                  <div className="countdown-number">{countdown}</div>
                  <p className="countdown-label">Get ready...</p>
                </div>
              )}
              {recording && (
                <div className="recording-indicator">
                  <div className="rec-dot-live" />
                  <span>REC {Math.ceil(recordTime)}s</span>
                  <div className="rec-bar">
                    <div className="rec-bar-fill" style={{ width: `${progress}%` }} />
                  </div>
                </div>
              )}
            </div>
            {!recording && countdown === 0 && (
              <button className="btn btn-primary" onClick={handleStartRecording} disabled={!cameraReady}>
                {cameraReady ? '🔴 Start Recording (5s)' : 'Waiting for camera...'}
              </button>
            )}
          </div>
        )}

        {/* Step 3: Results */}
        {step === 3 && (
          <div className="step-content fade-in">
            {loading && !result && (
              <div className="processing-state">
                <div className="processing-spinner" />
                <h3>Running Hybrid Analysis...</h3>
                <p>Traditional pipeline + VLM reasoning (may take 15-60 seconds)</p>
                <div className="processing-steps">
                  <div className="p-step active">🔍 Extracting video frames</div>
                  <div className="p-step">🧬 Face Detection & Alignment</div>
                  <div className="p-step">👤 ArcFace Identity Verification</div>
                  <div className="p-step">💓 Liveness Detection</div>
                  <div className="p-step">🛡️ Deepfake Analysis</div>
                  <div className="p-step">🧠 VLM Reasoning (Visual AI Judge)</div>
                </div>
              </div>
            )}

            {result && (
              <div className={`auth-result ${result.authenticated ? 'success' : 'failure'}`}>
                <div className="result-icon">
                  {result.authenticated ? '✅' : '❌'}
                </div>
                <h2 className="result-title">
                  {result.authenticated ? 'Access Granted' : 'Access Denied'}
                </h2>
                <p className="result-subtitle">
                  {result.authenticated
                    ? `Confidence: ${(result.confidence * 100).toFixed(1)}%`
                    : `Reason: ${result.denial_reason || 'Unknown'}`}
                </p>

                {/* VLM Override Warning */}
                {result.vlm_override && (
                  <div className="alert alert-error" style={{ marginTop: '12px' }}>
                    <span>🧠⚠️</span>
                    <div className="alert-content">
                      <div className="alert-title">VLM Override</div>
                      <div className="alert-detail">Traditional pipeline granted access, but VLM analysis detected issues and overrode the decision.</div>
                    </div>
                  </div>
                )}

                {/* Traditional Scores */}
                <div className="vlm-section">
                  <h3 className="vlm-section-title">📊 Traditional Pipeline</h3>
                  <div className="scores-grid">
                    <ScoreBar label="Face Match" value={result.scores?.traditional?.similarity} threshold={0.4} />
                    <ScoreBar label="Liveness" value={result.scores?.traditional?.liveness} threshold={0.7} />
                    <ScoreBar label="Deepfake" value={result.scores?.traditional?.deepfake} threshold={0.3} inverted />
                  </div>
                  <div className="result-meta">
                    <span>Traditional: {result.traditional_decision} ({(result.traditional_confidence * 100).toFixed(1)}%)</span>
                  </div>
                </div>

                {/* VLM Scores */}
                {result.vlm_invoked && result.scores?.vlm && (
                  <div className="vlm-section">
                    <h3 className="vlm-section-title">🧠 VLM Analysis</h3>
                    <div className="vlm-model-badge">
                      Model: <strong>{result.vlm_model_used}</strong>
                    </div>
                    <div className="scores-grid">
                      <ScoreBar label="VLM Identity" value={result.scores.vlm.vlm_identity} threshold={0.6} />
                      <ScoreBar label="VLM Liveness" value={result.scores.vlm.vlm_liveness} threshold={0.55} />
                      <ScoreBar label="VLM Authenticity" value={result.scores.vlm.vlm_authenticity} threshold={0.55} />
                      <ScoreBar label="VLM Overall" value={result.scores.vlm.vlm_overall} threshold={0.55} />
                    </div>
                  </div>
                )}

                {/* VLM Reasoning */}
                {result.vlm_reasoning && (
                  <div className="vlm-section">
                    <h3 className="vlm-section-title">💬 AI Reasoning</h3>
                    <div className="vlm-reasoning-box">
                      <div className="vlm-reasoning-text">
                        {result.vlm_reasoning.split('\n').map((line, i) => (
                          <p key={i}>{line}</p>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* No VLM refs warning */}
                {!result.has_vlm_refs && (
                  <div className="alert alert-info" style={{ marginTop: '12px' }}>
                    <span>ℹ️</span>
                    <div className="alert-content">
                      <div className="alert-title">VLM Reference Frames Missing</div>
                      <div className="alert-detail">
                        This user was registered without VLM. For full VLM analysis,
                        please re-register using the VLM Register page.
                      </div>
                    </div>
                  </div>
                )}

                {/* Threat flags */}
                {result.threat_flags?.length > 0 && (
                  <div className="threat-flags">
                    <h4>Security Flags</h4>
                    {result.threat_flags.map((flag, i) => (
                      <span key={i} className="threat-badge">{flag}</span>
                    ))}
                  </div>
                )}

                <div className="result-meta">
                  <span>Total Processing: {result.processing_time_ms?.toFixed(0)}ms</span>
                  {result.vlm_invoked && <span> | VLM: {result.vlm_model_used}</span>}
                </div>

                <button className="btn btn-secondary" onClick={handleReset}>Try Again</button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ScoreBar — reused from Login.jsx pattern */
function ScoreBar({ label, value, threshold, inverted = false }) {
  if (value === undefined || value === null) return null;
  const pct = Math.min(Math.max(value, 0), 1) * 100;
  const isGood = inverted ? value < threshold : value >= threshold;
  return (
    <div className="score-bar-item">
      <div className="score-bar-header">
        <span className="score-label">{label}</span>
        <span className={`score-value ${isGood ? 'good' : 'bad'}`}>{pct.toFixed(1)}%</span>
      </div>
      <div className="score-bar-track">
        <div className={`score-bar-fill ${isGood ? 'good' : 'bad'}`} style={{ width: `${pct}%` }} />
        <div className="score-bar-threshold" style={{ left: `${threshold * 100}%` }} />
      </div>
    </div>
  );
}
