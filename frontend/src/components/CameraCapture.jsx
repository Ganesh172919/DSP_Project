import React, { useRef, useState, useCallback, useEffect } from 'react';

/**
 * CameraCapture — Reusable camera component.
 *
 * Props:
 *   mode: "single" | "multi"  (single frame vs 5-frame sequence)
 *   onCapture: (blobs: Blob[]) => void  — callback with captured JPEG blobs
 *   disabled: bool
 */
export default function CameraCapture({ mode = 'single', onCapture, disabled = false }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [capturing, setCapturing] = useState(false);
  const [frameCount, setFrameCount] = useState(0);
  const totalFrames = mode === 'multi' ? 5 : 1;

  /* ─── Start camera ───────────────────────────────────────── */
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false,
      });
      streamRef.current = stream;
      // Set state first — this causes React to render the <video> element
      setCameraActive(true);
      // srcObject will be connected via the useEffect below
    } catch (err) {
      console.error('Camera access denied:', err);
      alert('Camera access is required. Please allow camera permissions.');
    }
  }, []);

  /* ─── Connect stream to video element after it mounts ────── */
  useEffect(() => {
    if (cameraActive && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [cameraActive]);

  /* ─── Stop camera ────────────────────────────────────────── */
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  }, []);

  /* ─── Grab a single JPEG frame from the video ────────────── */
  const grabFrame = useCallback(() => {
    return new Promise((resolve) => {
      const video = videoRef.current;
      if (!video) return resolve(null);

      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.92);
    });
  }, []);

  /* ─── Capture flow ───────────────────────────────────────── */
  const handleCapture = useCallback(async () => {
    if (!cameraActive || capturing || disabled) return;

    setCapturing(true);
    setFrameCount(0);
    const blobs = [];

    if (mode === 'multi') {
      /* Capture 5 frames over 5 seconds */
      for (let i = 0; i < totalFrames; i++) {
        setFrameCount(i + 1);
        const blob = await grabFrame();
        if (blob) blobs.push(blob);
        if (i < totalFrames - 1) {
          await new Promise((r) => setTimeout(r, 1000));
        }
      }
    } else {
      /* Single frame */
      setFrameCount(1);
      const blob = await grabFrame();
      if (blob) blobs.push(blob);
    }

    setCapturing(false);
    setFrameCount(0);
    if (blobs.length > 0 && onCapture) {
      onCapture(blobs);
    }
  }, [cameraActive, capturing, disabled, mode, totalFrames, grabFrame, onCapture]);

  /* ─── Cleanup on unmount ─────────────────────────────────── */
  useEffect(() => {
    return () => stopCamera();
  }, [stopCamera]);

  /* ─── Render ─────────────────────────────────────────────── */
  return (
    <div>
      <div className={`camera-container ${cameraActive ? 'active' : ''}`}>
        {cameraActive ? (
          <>
            <video
              ref={videoRef}
              className="camera-video"
              autoPlay
              playsInline
              muted
            />
            {capturing && (
              <div className="camera-overlay">
                <div className="capture-progress">
                  <div className="count">
                    {frameCount}/{totalFrames}
                  </div>
                  <div className="label">
                    {mode === 'multi' ? 'Capturing frames...' : 'Processing...'}
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="camera-placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
            <span style={{ fontSize: '14px' }}>Camera preview</span>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        {!cameraActive ? (
          <button
            className="btn btn-secondary"
            onClick={startCamera}
            disabled={disabled}
            id="btn-start-camera"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
              <circle cx="12" cy="13" r="4" />
            </svg>
            Start Camera
          </button>
        ) : (
          <>
            <button
              className="btn btn-primary"
              onClick={handleCapture}
              disabled={capturing || disabled}
              id="btn-capture"
              style={{ flex: 1 }}
            >
              {capturing ? (
                <>
                  <div className="spinner" />
                  Capturing...
                </>
              ) : (
                <>
                  {mode === 'multi' ? '📸 Start Capture (5 frames)' : '📸 Capture'}
                </>
              )}
            </button>
            <button
              className="btn btn-secondary"
              onClick={stopCamera}
              disabled={capturing}
              style={{ flex: 0, padding: '14px 16px' }}
            >
              ✕
            </button>
          </>
        )}
      </div>
    </div>
  );
}
