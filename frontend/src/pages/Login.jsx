import React, { useState, useRef, useCallback, useEffect } from 'react';
import client from '../api/client';

/* ── Icon SVGs ─────────────────────────────────────────────────────────── */
const LockIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="icon-sm">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

/**
 * Login page — 3-step video-based authentication:
 *
 * Step 1: Enter username
 * Step 2: Record a short video (4 seconds)
 * Step 3: Submit → Show results
 */
export default function Login() {
  const [step, setStep] = useState(1);
  const [username, setUsername] = useState('');
  const [videoBlob, setVideoBlob] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Camera refs
  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  // Recording state
  const [cameraReady, setCameraReady] = useState(false);
  const [recording, setRecording] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [recordTime, setRecordTime] = useState(4);
  const RECORD_DURATION = 4; // seconds

  // ── Step 1 → Step 2: Start camera ────────────────────────────────────
  const handleNext = useCallback(async () => {
    if (!username.trim()) {
      setError('Please enter your username');
      return;
    }
    setError('');
    setStep(2);
    // Start camera
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraReady(true);
    } catch (err) {
      setError('Camera access denied. Please allow camera permissions.');
      setStep(1);
    }
  }, [username]);

  // ── Start recording with countdown ───────────────────────────────────
  const handleStartRecording = useCallback(() => {
    setCountdown(3);
  }, []);

  // Countdown timer
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => {
      if (countdown === 1) {
        // Start actual recording
        beginRecording();
        setCountdown(0);
      } else {
        setCountdown(countdown - 1);
      }
    }, 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  const beginRecording = useCallback(() => {
    if (!streamRef.current) return;
    chunksRef.current = [];

    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9'
      : 'video/webm';

    const recorder = new MediaRecorder(streamRef.current, { mimeType });
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: mimeType });
      setVideoBlob(blob);
      setRecording(false);
      // Stop camera
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
      }
      // Auto-advance to submit
      setStep(3);
    };

    mediaRecorderRef.current = recorder;
    recorder.start(100);
    setRecording(true);
    setRecordTime(RECORD_DURATION);

    // Auto-stop after duration
    setTimeout(() => {
      if (recorder.state === 'recording') recorder.stop();
    }, RECORD_DURATION * 1000);
  }, []);

  // Recording timer
  useEffect(() => {
    if (!recording) return;
    const timer = setInterval(() => {
      setRecordTime(prev => {
        if (prev <= 0.1) { clearInterval(timer); return 0; }
        return prev - 0.1;
      });
    }, 100);
    return () => clearInterval(timer);
  }, [recording]);

  // ── Step 3: Submit video ─────────────────────────────────────────────
  const handleSubmit = useCallback(async () => {
    if (!videoBlob) {
      setError('No video recorded');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('video', videoBlob, 'auth_video.webm');

      const resp = await client.post('/authenticate/video', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      });
      setResult(resp.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed');
    }
    setLoading(false);
  }, [username, videoBlob]);

  // Auto-submit when step 3 reached
  useEffect(() => {
    if (step === 3 && videoBlob && !result && !loading) {
      handleSubmit();
    }
  }, [step, videoBlob, result, loading, handleSubmit]);

  // Cleanup camera on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  // Reset
  const handleReset = () => {
    setStep(1);
    setUsername('');
    setVideoBlob(null);
    setResult(null);
    setError('');
    setLoading(false);
    setCameraReady(false);
    setRecording(false);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
    }
  };

  const progress = ((RECORD_DURATION - recordTime) / RECORD_DURATION) * 100;

  return (
    <div className="page">
      <div className="card login-card">
        {/* Header */}
        <div className="card-header">
          <div className="card-icon"><LockIcon /></div>
          <h1>Authenticate</h1>
          <p className="card-subtitle">Record a short video to verify your identity</p>
        </div>

        {/* Progress stepper */}
        <div className="stepper">
          {['Username', 'Record Video', 'Verify'].map((label, i) => (
            <div key={i} className={`step-dot ${step > i + 1 ? 'completed' : ''} ${step === i + 1 ? 'active' : ''}`}>
              <div className="dot">{step > i + 1 ? '✓' : i + 1}</div>
              <span className="step-label">{label}</span>
            </div>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="alert alert-error">
            <span>⚠️</span> {error}
          </div>
        )}

        {/* ── Step 1: Username ──────────────────────────────────────── */}
        {step === 1 && (
          <div className="step-content fade-in">
            <div className="form-group">
              <label htmlFor="login-username">Username</label>
              <input
                id="login-username"
                type="text"
                className="form-input"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="Enter your registered username"
                onKeyDown={e => e.key === 'Enter' && handleNext()}
                autoFocus
              />
            </div>
            <button
              className="btn btn-primary"
              onClick={handleNext}
              disabled={!username.trim()}
            >
              Next →
            </button>
          </div>
        )}

        {/* ── Step 2: Record Video ─────────────────────────────────── */}
        {step === 2 && (
          <div className="step-content fade-in">
            <div className="video-instructions">
              <p>Look directly at the camera and keep your face visible.</p>
              <p className="video-hint">The system will analyze your video for face matching, liveness, and security checks.</p>
            </div>

            <div className="camera-container active">
              <video ref={videoRef} autoPlay playsInline muted className="camera-video" />

              {/* Countdown overlay */}
              {countdown > 0 && (
                <div className="countdown-overlay">
                  <div className="countdown-number">{countdown}</div>
                  <p className="countdown-label">Get ready...</p>
                </div>
              )}

              {/* Recording overlay */}
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
              <button
                className="btn btn-primary"
                onClick={handleStartRecording}
                disabled={!cameraReady}
              >
                {cameraReady ? '🔴 Start Recording (4s)' : 'Waiting for camera...'}
              </button>
            )}
          </div>
        )}

        {/* ── Step 3: Processing / Results ──────────────────────────── */}
        {step === 3 && (
          <div className="step-content fade-in">
            {loading && !result && (
              <div className="processing-state">
                <div className="processing-spinner" />
                <h3>Analyzing your video...</h3>
                <p>Running face recognition, liveness detection, and deepfake analysis</p>
                <div className="processing-steps">
                  <div className="p-step active">🔍 Extracting video frames</div>
                  <div className="p-step">🧬 Face Detection & Alignment</div>
                  <div className="p-step">👤 Identity Verification</div>
                  <div className="p-step">💓 Liveness Detection</div>
                  <div className="p-step">🛡️ Deepfake Analysis</div>
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
                    ? `Welcome back! Confidence: ${(result.confidence * 100).toFixed(1)}%`
                    : `Reason: ${result.denial_reason || 'Unknown'}`
                  }
                </p>

                {/* Scores breakdown */}
                <div className="scores-grid">
                  <ScoreBar label="Face Match" value={result.scores?.similarity} threshold={0.4} />
                  <ScoreBar label="Liveness" value={result.scores?.liveness} threshold={0.7} />
                  <ScoreBar label="Deepfake" value={result.scores?.deepfake} threshold={0.3} inverted />
                </div>

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
                  <span>Processing: {result.processing_time_ms?.toFixed(0)}ms</span>
                </div>

                <button className="btn btn-secondary" onClick={handleReset}>
                  Try Again
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── ScoreBar Component ────────────────────────────────────────────────── */
function ScoreBar({ label, value, threshold, inverted = false }) {
  if (value === undefined || value === null) return null;

  const pct = Math.min(Math.max(value, 0), 1) * 100;
  const isGood = inverted ? value < threshold : value >= threshold;

  return (
    <div className="score-bar-item">
      <div className="score-bar-header">
        <span className="score-label">{label}</span>
        <span className={`score-value ${isGood ? 'good' : 'bad'}`}>
          {pct.toFixed(1)}%
        </span>
      </div>
      <div className="score-bar-track">
        <div
          className={`score-bar-fill ${isGood ? 'good' : 'bad'}`}
          style={{ width: `${pct}%` }}
        />
        <div
          className="score-bar-threshold"
          style={{ left: `${threshold * 100}%` }}
        />
      </div>
    </div>
  );
}
