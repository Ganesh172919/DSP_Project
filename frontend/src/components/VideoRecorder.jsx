import React, { useRef, useState, useEffect, useCallback } from 'react';

/**
 * VideoRecorder — Records video from webcam using MediaRecorder API.
 * Returns a Blob (WebM) when recording is complete.
 *
 * Props:
 *   stream:       MediaStream from getUserMedia
 *   duration:     recording duration in seconds
 *   onComplete:   callback(videoBlob) when done
 *   autoStart:    start recording immediately
 *   recording:    external control — true to start
 */
export default function VideoRecorder({ stream, duration = 4, onComplete, autoStart = false, recording: externalRecording }) {
  const mediaRecorder = useRef(null);
  const chunks = useRef([]);
  const [isRecording, setIsRecording] = useState(false);
  const [timeLeft, setTimeLeft] = useState(duration);

  const stopRecording = useCallback(() => {
    if (mediaRecorder.current && mediaRecorder.current.state === 'recording') {
      mediaRecorder.current.stop();
    }
  }, []);

  const startRecording = useCallback(() => {
    if (!stream) return;
    chunks.current = [];

    const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
      ? 'video/webm;codecs=vp9'
      : MediaRecorder.isTypeSupported('video/webm;codecs=vp8')
        ? 'video/webm;codecs=vp8'
        : 'video/webm';

    const recorder = new MediaRecorder(stream, { mimeType });

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.current.push(e.data);
    };

    recorder.onstop = () => {
      setIsRecording(false);
      const blob = new Blob(chunks.current, { type: mimeType });
      if (onComplete) onComplete(blob);
    };

    mediaRecorder.current = recorder;
    recorder.start(100); // collect data every 100ms
    setIsRecording(true);
    setTimeLeft(duration);

    // Auto-stop after duration
    setTimeout(() => {
      stopRecording();
    }, duration * 1000);
  }, [stream, duration, onComplete, stopRecording]);

  // Countdown timer
  useEffect(() => {
    if (!isRecording) return;
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 0.1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 0.1;
      });
    }, 100);
    return () => clearInterval(timer);
  }, [isRecording]);

  // Auto-start
  useEffect(() => {
    if (autoStart && stream && !isRecording) {
      startRecording();
    }
  }, [autoStart, stream]);

  // External control
  useEffect(() => {
    if (externalRecording && stream && !isRecording) {
      startRecording();
    }
  }, [externalRecording]);

  const progress = ((duration - timeLeft) / duration) * 100;

  return (
    <div className="video-recorder">
      {isRecording && (
        <div className="recording-overlay">
          <div className="rec-dot" />
          <span className="rec-timer">{Math.ceil(timeLeft)}s</span>
          <div className="rec-progress-bar">
            <div className="rec-progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}
    </div>
  );
}
