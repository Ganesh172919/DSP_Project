import React, { useRef, useState, useEffect, useCallback } from 'react';

/**
 * InstructionChallenge — Displays instruction + records response video.
 *
 * Props:
 *   instruction:   { id, text, category, duration_sec }
 *   onComplete:    callback(videoBlob, instructionId) when done
 *   stepNumber:    which step (1 or 2)
 *   totalSteps:    total number of steps
 */
export default function InstructionChallenge({ instruction, onComplete, stepNumber = 1, totalSteps = 2 }) {
  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const [stream, setStream] = useState(null);
  const [phase, setPhase] = useState('prepare'); // 'prepare' | 'countdown' | 'recording' | 'done'
  const [countdown, setCountdown] = useState(3);
  const [recordTime, setRecordTime] = useState(instruction?.duration_sec || 4);

  // Start camera
  useEffect(() => {
    let s = null;
    (async () => {
      try {
        s = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480, facingMode: 'user' },
          audio: false,
        });
        setStream(s);
        if (videoRef.current) {
          videoRef.current.srcObject = s;
        }
      } catch (err) {
        console.error('Camera access error:', err);
      }
    })();
    return () => {
      if (s) s.getTracks().forEach(t => t.stop());
    };
  }, []);

  // Attach stream to video element
  useEffect(() => {
    if (stream && videoRef.current) {
      videoRef.current.srcObject = stream;
    }
  }, [stream]);

  // Start countdown when user clicks begin
  const handleBegin = useCallback(() => {
    setPhase('countdown');
    setCountdown(3);
  }, []);

  // Countdown timer
  useEffect(() => {
    if (phase !== 'countdown') return;
    if (countdown <= 0) {
      setPhase('recording');
      return;
    }
    const timer = setTimeout(() => setCountdown(c => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [phase, countdown]);

  // Start recording when phase changes to 'recording'
  useEffect(() => {
    if (phase !== 'recording' || !stream) return;
    chunksRef.current = [];

    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9'
      : 'video/webm';

    const recorder = new MediaRecorder(stream, { mimeType });
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: mimeType });
      setPhase('done');
      if (onComplete) onComplete(blob, instruction.id);
    };

    mediaRecorderRef.current = recorder;
    recorder.start(100);
    setRecordTime(instruction?.duration_sec || 4);

    // Auto-stop after duration
    const timer = setTimeout(() => {
      if (recorder.state === 'recording') recorder.stop();
    }, (instruction?.duration_sec || 4) * 1000);

    return () => clearTimeout(timer);
  }, [phase, stream, instruction, onComplete]);

  // Recording countdown
  useEffect(() => {
    if (phase !== 'recording') return;
    const timer = setInterval(() => {
      setRecordTime(prev => {
        if (prev <= 0.1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 0.1;
      });
    }, 100);
    return () => clearInterval(timer);
  }, [phase]);

  const duration = instruction?.duration_sec || 4;
  const progress = phase === 'recording' ? ((duration - recordTime) / duration) * 100 : 0;

  return (
    <div className="instruction-challenge">
      {/* Step indicator */}
      <div className="step-indicator">
        <span className="step-badge">Challenge {stepNumber} of {totalSteps}</span>
        <span className={`category-badge ${instruction?.category}`}>
          {instruction?.category === 'face' ? '🎭 Face' : '🤚 Hand'}
        </span>
      </div>

      {/* Instruction text */}
      <div className={`instruction-card ${phase === 'recording' ? 'active' : ''}`}>
        <p className="instruction-text">{instruction?.text || 'Loading...'}</p>
      </div>

      {/* Camera preview */}
      <div className="camera-container challenge-camera">
        <video ref={videoRef} autoPlay playsInline muted className="camera-video" />

        {/* Countdown overlay */}
        {phase === 'countdown' && (
          <div className="countdown-overlay">
            <div className="countdown-number">{countdown}</div>
            <p className="countdown-label">Get ready...</p>
          </div>
        )}

        {/* Recording overlay */}
        {phase === 'recording' && (
          <div className="recording-indicator">
            <div className="rec-dot-live" />
            <span>REC {Math.ceil(recordTime)}s</span>
            <div className="rec-bar">
              <div className="rec-bar-fill" style={{ width: `${progress}%` }} />
            </div>
          </div>
        )}

        {/* Done overlay */}
        {phase === 'done' && (
          <div className="done-overlay">
            <div className="done-checkmark">✓</div>
            <p>Captured!</p>
          </div>
        )}
      </div>

      {/* Action button */}
      {phase === 'prepare' && (
        <button
          className="btn btn-primary challenge-btn"
          onClick={handleBegin}
          disabled={!stream}
        >
          {stream ? 'Begin Recording' : 'Waiting for camera...'}
        </button>
      )}
    </div>
  );
}
