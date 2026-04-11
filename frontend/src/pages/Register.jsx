import React, { useState, useCallback } from 'react';
import CameraCapture from '../components/CameraCapture';
import client from '../api/client';

export default function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);   // { type: 'success'|'error', data }

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

        /* Send all captured frames as separate files */
        blobs.forEach((blob, i) => {
          formData.append('face_data', blob, `face_${i}.jpg`);
        });

        const res = await client.post('/register', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
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
      <div className="card" id="register-card">
        {/* ─── Header ──────────────────────────────────── */}
        <div className="card-header">
          <h1>Create Account</h1>
          <p>Register your face for secure authentication</p>
        </div>

        {/* ─── Form Fields ─────────────────────────────── */}
        <div className="form-group">
          <label htmlFor="reg-name">Full Name</label>
          <input
            id="reg-name"
            className="form-input"
            type="text"
            placeholder="John Doe"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="reg-email">Email Address</label>
          <input
            id="reg-email"
            className="form-input"
            type="email"
            placeholder="john@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
          />
        </div>

        {/* ─── Camera ──────────────────────────────────── */}
        <CameraCapture
          mode="multi"
          onCapture={handleCapture}
          disabled={loading || !name.trim() || !email.trim()}
        />

        {/* ─── Loading State ───────────────────────────── */}
        {loading && (
          <div className="alert alert-info">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v6l4 2" />
            </svg>
            <div className="alert-content">
              <div className="alert-title">Processing registration...</div>
              <div className="alert-detail">Running liveness check and embedding extraction</div>
            </div>
          </div>
        )}

        {/* ─── Result ──────────────────────────────────── */}
        {result?.type === 'success' && (
          <div className="alert alert-success">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <div className="alert-content">
              <div className="alert-title">Registered ✓</div>
              <div className="alert-detail">
                User ID: {result.data.user_id} — Face quality: {(result.data.face_quality * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        )}

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
