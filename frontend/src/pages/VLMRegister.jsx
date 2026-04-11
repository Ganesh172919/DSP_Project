import React, { useState, useRef, useCallback, useEffect } from 'react';
import client from '../api/client';

/**
 * VLMRegister — Video-based registration page for VLM hybrid auth.
 *
 * Records a 5-second video and sends it to the VLM registration endpoint.
 * The backend extracts frames for both traditional embedding + VLM reference storage.
 */
export default function VLMRegister() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [step, setStep] = useState(1); // 1: form, 2: record, 3: result
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
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

  // Start camera
  const handleNext = useCallback(async () => {
    if (!name.trim() || !email.trim()) {
      setError('Please fill in both name and email.');
      return;
    }
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
      setError('Camera access denied. Please allow camera permissions.');
      setStep(1);
    }
  }, [name, email]);

  // Countdown
  const handleStartRecording = useCallback(() => setCountdown(3), []);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => {
      if (countdown === 1) {
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
      ? 'video/webm;codecs=vp9' : 'video/webm';
    const recorder = new MediaRecorder(streamRef.current, { mimeType });
    recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: mimeType });
      setRecording(false);
      if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
      submitVideo(blob);
    };
    mediaRecorderRef.current = recorder;
    recorder.start(100);
    setRecording(true);
    setRecordTime(RECORD_DURATION);
    setTimeout(() => { if (recorder.state === 'recording') recorder.stop(); }, RECORD_DURATION * 1000);
  }, []);

  // Recording timer
  useEffect(() => {
    if (!recording) return;
    const timer = setInterval(() => {
      setRecordTime(prev => { if (prev <= 0.1) { clearInterval(timer); return 0; } return prev - 0.1; });
    }, 100);
    return () => clearInterval(timer);
  }, [recording]);

  // Submit video
  const submitVideo = useCallback(async (blob) => {
    setStep(3);
    setLoading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('username', name.trim());
      formData.append('email', email.trim());
      formData.append('video', blob, 'reg_video.webm');
      const resp = await client.post('/vlm/register', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 180000,
      });
      setResult({ type: 'success', data: resp.data });
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Registration failed';
      setResult({ type: 'error', data: { message: msg } });
    }
    setLoading(false);
  }, [name, email]);

  // Cleanup
  useEffect(() => () => {
    if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
  }, []);

  const handleReset = () => {
    setStep(1); setName(''); setEmail(''); setResult(null); setError('');
    setLoading(false); setCameraReady(false); setRecording(false);
    if (streamRef.current) streamRef.current.getTracks().forEach(t => t.stop());
  };

  const progress = ((RECORD_DURATION - recordTime) / RECORD_DURATION) * 100;

  return (
    <div className="page">
      <div className="card" id="vlm-register-card">
        {/* Header */}
        <div className="card-header">
          <div className="vlm-badge">
            <span className="vlm-badge-icon">🧠</span>
            <span>VLM Enhanced</span>
          </div>
          <h1>VLM Registration</h1>
          <p>Record a 5-second video for AI-powered face registration</p>
        </div>

        {/* Stepper */}
        <div className="stepper">
          {['Details', 'Record Video', 'Register'].map((label, i) => (
            <div key={i} className={`step-dot ${step > i + 1 ? 'completed' : ''} ${step === i + 1 ? 'active' : ''}`}>
              <div className="dot">{step > i + 1 ? '✓' : i + 1}</div>
              <span className="step-label">{label}</span>
            </div>
          ))}
        </div>

        {error && (
          <div className="alert alert-error"><span>⚠️</span> {error}</div>
        )}

        {/* Step 1: Form */}
        {step === 1 && (
          <div className="step-content fade-in">
            <div className="form-group">
              <label htmlFor="vlm-reg-name">Full Name</label>
              <input id="vlm-reg-name" className="form-input" type="text"
                placeholder="John Doe" value={name}
                onChange={e => setName(e.target.value)} disabled={loading} />
            </div>
            <div className="form-group">
              <label htmlFor="vlm-reg-email">Email Address</label>
              <input id="vlm-reg-email" className="form-input" type="email"
                placeholder="john@example.com" value={email}
                onChange={e => setEmail(e.target.value)} disabled={loading} />
            </div>
            <div className="vlm-info-box">
              <h4>🧠 VLM Registration</h4>
              <p>This registers your face using both traditional AI models and a Vision Language Model.
                A 5-second video will be recorded to capture your face from slightly different angles.</p>
              <ul>
                <li>Traditional: ArcFace embedding + liveness check</li>
                <li>VLM: 3 reference frames stored for semantic reasoning</li>
              </ul>
            </div>
            <button className="btn btn-primary" onClick={handleNext}
              disabled={!name.trim() || !email.trim()}>
              Next → Start Camera
            </button>
          </div>
        )}

        {/* Step 2: Record */}
        {step === 2 && (
          <div className="step-content fade-in">
            <div className="video-instructions">
              <p>Look directly at the camera. Move your head slightly for the best registration.</p>
              <p className="video-hint">The 5-second video captures your face for both traditional and VLM analysis.</p>
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

        {/* Step 3: Result */}
        {step === 3 && (
          <div className="step-content fade-in">
            {loading && (
              <div className="processing-state">
                <div className="processing-spinner" />
                <h3>Processing VLM Registration...</h3>
                <p>This may take a moment as we set up both traditional and VLM profiles.</p>
                <div className="processing-steps">
                  <div className="p-step active">🎬 Extracting video frames</div>
                  <div className="p-step">🔍 Face detection & alignment</div>
                  <div className="p-step">🧬 ArcFace embedding extraction</div>
                  <div className="p-step">💓 Liveness verification</div>
                  <div className="p-step">🧠 Selecting VLM reference frames</div>
                  <div className="p-step">🔐 Encrypting & storing</div>
                </div>
              </div>
            )}

            {result?.type === 'success' && (
              <div className="auth-result success">
                <div className="result-icon">✅</div>
                <h2 className="result-title">VLM Registration Complete</h2>
                <p className="result-subtitle">
                  User ID: {result.data.user_id} — Face Quality: {(result.data.face_quality * 100).toFixed(1)}%
                </p>
                <div className="scores-grid">
                  <ScoreItem label="Face Quality" value={result.data.face_quality} icon="👤" />
                  <ScoreItem label="Liveness Score" value={result.data.liveness_score} icon="💓" />
                  <ScoreItem label="VLM Ref Frames" value={result.data.vlm_ref_frames_stored} isCount icon="🧠" />
                </div>
                <div className="vlm-info-box" style={{ marginTop: '16px' }}>
                  <p>✅ Traditional face profile + {result.data.vlm_ref_frames_stored} VLM reference frames stored.</p>
                  <p>You can now use <strong>VLM Login</strong> for AI-powered authentication.</p>
                </div>
                <button className="btn btn-secondary" onClick={handleReset}>Register Another</button>
              </div>
            )}

            {result?.type === 'error' && (
              <div className="auth-result failure">
                <div className="result-icon">❌</div>
                <h2 className="result-title">Registration Failed</h2>
                <p className="result-subtitle">{result.data.message}</p>
                <button className="btn btn-secondary" onClick={handleReset}>Try Again</button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* Score Item */
function ScoreItem({ label, value, icon, isCount = false }) {
  const display = isCount ? value : `${(value * 100).toFixed(1)}%`;
  return (
    <div className="vlm-score-item">
      <span className="vlm-score-icon">{icon}</span>
      <span className="vlm-score-label">{label}</span>
      <span className="vlm-score-value">{display}</span>
    </div>
  );
}
