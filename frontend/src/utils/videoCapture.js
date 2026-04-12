export function getPreferredVideoMimeType() {
  if (typeof MediaRecorder === 'undefined') {
    return 'video/webm';
  }

  if (MediaRecorder.isTypeSupported('video/webm;codecs=vp9')) {
    return 'video/webm;codecs=vp9';
  }

  if (MediaRecorder.isTypeSupported('video/webm;codecs=vp8')) {
    return 'video/webm;codecs=vp8';
  }

  return 'video/webm';
}

export function captureVideoFrame(videoElement, quality = 0.92) {
  return new Promise((resolve) => {
    if (!videoElement) {
      resolve(null);
      return;
    }

    const width = videoElement.videoWidth || 640;
    const height = videoElement.videoHeight || 480;
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;

    const context = canvas.getContext('2d');
    if (!context) {
      resolve(null);
      return;
    }

    context.drawImage(videoElement, 0, 0, width, height);
    canvas.toBlob((blob) => resolve(blob), 'image/jpeg', quality);
  });
}

export function scheduleFrameCaptures({
  videoElement,
  count = 3,
  durationMs,
  onFrame,
}) {
  const timers = [];

  if (!videoElement || count <= 0 || durationMs <= 0 || typeof onFrame !== 'function') {
    return () => {};
  }

  const spacingMs = durationMs / (count + 1);

  for (let index = 1; index <= count; index += 1) {
    const timerId = window.setTimeout(async () => {
      const blob = await captureVideoFrame(videoElement);
      if (blob) {
        onFrame(blob, index - 1);
      }
    }, Math.round(spacingMs * index));

    timers.push(timerId);
  }

  return () => {
    timers.forEach((timerId) => window.clearTimeout(timerId));
  };
}
