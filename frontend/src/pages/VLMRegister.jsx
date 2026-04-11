import React, { useState, useCallback } from 'react';
import CameraCapture from '../components/CameraCapture';
import client from '../api/client';

/**
 * VLMRegister — Registration page for VLM hybrid auth.
 *
 * Uses the SAME 5-frame capture as normal Register.
 * Sends frames to /api/v1/vlm/register which stores them on disk
 * for VLM comparison during authentication.
 */
export default function VLMRegister() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleCapture = useCallback(
    async (blobs) => {
      if (!name.trim() || !email.trim()) {
        setResult({ type: 'error', data: { message: 'Please fill in name and email.' } });
        return;
      }

      setLoading(true);
      setResult(null);

      try {
        const formData = new FormData();
        formData.append('username', name.trim());
        formData.append('email', email.trim());

        /* Send all captured frames as separate files — same as normal register */
        blobs.forEach((blob, i) => {
          formData.append('face_data', blob, `face_${i}.jpg`);
        });

        const res = await client.post('/vlm/register', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 120000,
        });

        setResult({ type: 'success', data: res.data });
      } catch (err) {
        const msg = err.response?.data?.detail || err.message || 'Registration failed';
        setResult({ type: 'error', data: { message: msg } });
      } finally {
        setLoading(false);
      }
    },
    [name, email]
  );

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
          <p>Register your face for AI-powered hybrid authentication</p>
        </div>

        {/* Info Box */}
        <div className="vlm-info-box">
          <h4>🧠 What's different?</h4>
          <p>This uses the same 5-frame capture as normal registration, but also stores your face reference frames for VLM (Vision Language Model) comparison during login.</p>
          <ul>
            <li><strong>Traditional:</strong> ArcFace embedding + liveness check</li>
            <li><strong>VLM Extra:</strong> Reference frames saved for semantic AI reasoning</li>
          </ul>
        </div>

        {/* Form Fields */}
        <div className="form-group">
          <label htmlFor="vlm-reg-name">Full Name</label>
          <input
            id="vlm-reg-name"
            className="form-input"
            type="text"
            placeholder="John Doe"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="vlm-reg-email">Email Address</label>
          <input
            id="vlm-reg-email"
            className="form-input"
            type="email"
            placeholder="john@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
          />
        </div>

        {/* Camera — same 5-frame multi capture as normal register */}
        <CameraCapture
          mode="multi"
          onCapture={handleCapture}
          disabled={loading || !name.trim() || !email.trim()}
        />

        {/* Loading State */}
        {loading && (
          <div className="alert alert-info">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v6l4 2" />
            </svg>
            <div className="alert-content">
              <div className="alert-title">Processing VLM registration...</div>
              <div className="alert-detail">Running liveness check, embedding extraction, and saving VLM reference frames</div>
            </div>
          </div>
        )}

        {/* Success */}
        {result?.type === 'success' && (
          <div className="alert alert-success">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <div className="alert-content">
              <div className="alert-title">VLM Registration Complete ✓</div>
              <div className="alert-detail">
                User ID: {result.data.user_id} —
                Face quality: {(result.data.face_quality * 100).toFixed(1)}% —
                VLM frames: {result.data.vlm_ref_frames_stored} stored
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {result?.type === 'error' && (
          <div className="alert alert-error">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            <div className="alert-content">
              <div className="alert-title">Registration Failed</div>
              <div className="alert-detail">{result.data.message}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
