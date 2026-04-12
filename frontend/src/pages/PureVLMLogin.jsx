import React, { useCallback, useEffect, useRef, useState } from 'react';
import client from '../api/client';
import {
  getPreferredVideoMimeType,
  scheduleFrameCaptures,
} from '../utils/videoCapture';

const EyeIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="icon-sm">
    <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const RECORD_DURATION = 3;
const AUTH_FRAME_COUNT = 3;

export default function PureVLMLogin() {
  const [step, setStep] = useState(1);
  const [username, setUsername] = useState('');
  const [videoBlob, setVideoBlob] = useState(null);
  const [authFrameBlobs, setAuthFrameBlobs] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [cameraReady, setCameraReady] = useState(false);
  const [recording, setRecording] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [recordTime, setRecordTime] = useState(RECORD_DURATION);
  const [warmupState, setWarmupState] = useState('idle');
  const [warmupError, setWarmupError] = useState('');

  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const authFramesRef = useRef([]);
  const frameCaptureCleanupRef = useRef(() => {});

  const stopStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  const handleNext = useCallback(async () => {
    if (!username.trim()) {
      setError('Please enter your username');
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
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraReady(true);
    } catch {
      setError('Camera access denied. Please allow camera permissions.');
      setStep(1);
    }
  }, [username]);

  const beginRecording = useCallback(() => {
    if (!streamRef.current) {
      return;
    }

    chunksRef.current = [];
    authFramesRef.current = [];
    setAuthFrameBlobs([]);

    const mimeType = getPreferredVideoMimeType();
    const recorder = new MediaRecorder(streamRef.current, { mimeType });

    frameCaptureCleanupRef.current();
    frameCaptureCleanupRef.current = scheduleFrameCaptures({
      videoElement: videoRef.current,
      count: AUTH_FRAME_COUNT,
      durationMs: RECORD_DURATION * 1000,
      onFrame: (blob) => {
        authFramesRef.current.push(blob);
      },
    });

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };

    recorder.onstop = () => {
      frameCaptureCleanupRef.current();
      const blob = new Blob(chunksRef.current, { type: mimeType });
      setVideoBlob(blob);
      setAuthFrameBlobs([...authFramesRef.current]);
      setRecording(false);
      stopStream();
      setStep(3);
    };

    mediaRecorderRef.current = recorder;
    recorder.start(100);
    setRecording(true);
    setRecordTime(RECORD_DURATION);

    window.setTimeout(() => {
      if (recorder.state === 'recording') {
        recorder.stop();
      }
    }, RECORD_DURATION * 1000);
  }, [stopStream]);

  const handleStartRecording = useCallback(() => {
    setCountdown(3);
  }, []);

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
      authFrameBlobs.forEach((blob, index) => {
        formData.append('auth_frames', blob, `pure_auth_frame_${index}.jpg`);
      });

      const response = await client.post('/vlm/authenticate/pure', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 900000,
      });

      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Pure VLM authentication failed');
    }

    setLoading(false);
  }, [authFrameBlobs, username, videoBlob]);

  const handleReset = useCallback(() => {
    setStep(1);
    setUsername('');
    setVideoBlob(null);
    setAuthFrameBlobs([]);
    setResult(null);
    setLoading(false);
    setError('');
    setCameraReady(false);
    setRecording(false);
    setCountdown(0);
    setRecordTime(RECORD_DURATION);
    authFramesRef.current = [];
    frameCaptureCleanupRef.current();
    stopStream();
  }, [stopStream]);

  useEffect(() => {
    let cancelled = false;

    const warmModel = async () => {
      setWarmupState('warming');
      setWarmupError('');
      try {
        const response = await client.post('/vlm/warmup', null, {
          timeout: 900000,
        });
        if (!cancelled) {
          setWarmupState(response.data?.ready ? 'ready' : 'error');
          if (!response.data?.ready) {
            setWarmupError(response.data?.vlm?.error || 'VLM warmup did not complete');
          }
        }
      } catch (err) {
        if (!cancelled) {
          setWarmupState('error');
          setWarmupError(err.response?.data?.detail || err.message || 'VLM warmup failed');
        }
      }
    };

    warmModel();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (countdown <= 0) {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      if (countdown === 1) {
        beginRecording();
        setCountdown(0);
      } else {
        setCountdown((previous) => previous - 1);
      }
    }, 1000);

    return () => window.clearTimeout(timer);
  }, [beginRecording, countdown]);

  useEffect(() => {
    if (!recording) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setRecordTime((previous) => {
        if (previous <= 0.1) {
          window.clearInterval(timer);
          return 0;
        }
        return previous - 0.1;
      });
    }, 100);

    return () => window.clearInterval(timer);
  }, [recording]);

  useEffect(() => {
    if (step === 3 && videoBlob && !result && !loading) {
      handleSubmit();
    }
  }, [handleSubmit, loading, result, step, videoBlob]);

  useEffect(() => () => {
    frameCaptureCleanupRef.current();
    stopStream();
  }, [stopStream]);

  const progress = ((RECORD_DURATION - recordTime) / RECORD_DURATION) * 100;

  return (
    <div className="page">
      <div className="card login-card vlm-card">
        <div className="card-header">
          <div className="vlm-badge">
            <span className="vlm-badge-icon">VLM</span>
            <span>Pure VLM</span>
          </div>
          <div className="card-icon"><EyeIcon /></div>
          <h1>Pure VLM Authenticate</h1>
          <p className="card-subtitle">Identity, liveness, and authenticity judged only by the VLM</p>
        </div>

        <div className="stepper">
          {['Username', 'Record 3s', 'Reason'].map((label, index) => (
            <div
              key={label}
              className={`step-dot ${step > index + 1 ? 'completed' : ''} ${step === index + 1 ? 'active' : ''}`}
            >
              <div className="dot">{step > index + 1 ? 'OK' : index + 1}</div>
              <span className="step-label">{label}</span>
            </div>
          ))}
        </div>

        {error && <div className="alert alert-error"><span>!</span> {error}</div>}

        {step === 1 && (
          <div className="step-content fade-in">
            <div className="form-group">
              <label htmlFor="pure-vlm-username">Username</label>
              <input
                id="pure-vlm-username"
                type="text"
                className="form-input"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Enter your VLM-registered username"
                onKeyDown={(event) => event.key === 'Enter' && handleNext()}
                autoFocus
              />
            </div>

            <div className="vlm-info-box">
              <h4>Pure VLM mode</h4>
              <p>
                This path does not use ArcFace, liveness CNNs, or the traditional deepfake detector.
                It compares your stored VLM registration frames with 3 new frames from this recording.
              </p>
              <p className="warmup-status">
                {warmupState === 'warming' && 'Preparing VLM model in the background...'}
                {warmupState === 'ready' && 'VLM model is ready.'}
                {warmupState === 'error' && `VLM warmup issue: ${warmupError}`}
              </p>
            </div>

            <button className="btn btn-primary" onClick={handleNext} disabled={!username.trim()}>
              Next
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="step-content fade-in">
            <div className="video-instructions">
              <p>Hold steady, look into the camera, and keep your full face visible.</p>
              <p className="video-hint">We record 3 seconds and capture 3 still frames for the VLM.</p>
              {warmupState === 'warming' && (
                <p className="video-hint">Model warmup is still running. You can continue, but the first analysis may take longer.</p>
              )}
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
                {cameraReady ? 'Start Recording' : 'Waiting for camera...'}
              </button>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="step-content fade-in">
            {loading && !result && (
              <div className="processing-state">
                <div className="processing-spinner" />
                <h3>Running pure VLM analysis...</h3>
                <p>The first run can take longer while moondream downloads and loads on CPU.</p>
                <div className="processing-steps">
                  <div className="p-step active">Collecting VLM auth frames</div>
                  <div className="p-step">Loading VLM registration frames</div>
                  <div className="p-step">Identity and liveness reasoning</div>
                  <div className="p-step">Authenticity and spoof checks</div>
                </div>
              </div>
            )}

            {result && (
              <div className={`auth-result ${result.authenticated ? 'success' : 'failure'}`}>
                <div className="result-icon">{result.authenticated ? 'OK' : 'NO'}</div>
                <h2 className="result-title">
                  {result.authenticated ? 'Access Granted' : 'Access Denied'}
                </h2>
                <p className="result-subtitle">
                  {result.authenticated
                    ? `Confidence: ${(result.confidence * 100).toFixed(1)}%`
                    : `Reason: ${result.denial_reason || 'Unknown'}`}
                </p>

                <div className="vlm-section">
                  <h3 className="vlm-section-title">Pure VLM scores</h3>
                  <div className="vlm-model-badge">
                    Model: <strong>{result.vlm_model_used}</strong>
                  </div>
                  <div className="scores-grid">
                    <ScoreBar label="Identity" value={result.scores?.vlm_identity} threshold={0.6} />
                    <ScoreBar label="Liveness" value={result.scores?.vlm_liveness} threshold={0.55} />
                    <ScoreBar label="Authenticity" value={result.scores?.vlm_authenticity} threshold={0.55} />
                    <ScoreBar label="Overall" value={result.scores?.vlm_overall} threshold={0.55} />
                  </div>
                </div>

                {result.vlm_reasoning && (
                  <div className="vlm-section">
                    <h3 className="vlm-section-title">AI reasoning</h3>
                    <div className="vlm-reasoning-box">
                      <div className="vlm-reasoning-text">
                        {result.vlm_reasoning.split('\n').map((line, index) => (
                          <p key={`${line}-${index}`}>{line || '\u00A0'}</p>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {result.vlm_red_flags?.length > 0 && (
                  <div className="threat-flags">
                    <h4>VLM flags</h4>
                    {result.vlm_red_flags.map((flag) => (
                      <span key={flag} className="threat-badge">{flag}</span>
                    ))}
                  </div>
                )}

                <div className="result-meta">
                  <span>Total: {result.processing_time_ms?.toFixed(0)}ms</span>
                  <span> | VLM frames: {result.auth_frames_used ?? authFrameBlobs.length}</span>
                </div>

                <button className="btn btn-secondary" onClick={handleReset} style={{ marginTop: '12px' }}>
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

function ScoreBar({ label, value, threshold }) {
  if (value === undefined || value === null) {
    return null;
  }

  const pct = Math.min(Math.max(value, 0), 1) * 100;
  const isGood = value >= threshold;

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
