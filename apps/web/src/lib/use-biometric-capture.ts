import { useEffect, useMemo, useRef, useState } from "react";
import {
  FaceLandmarker,
  FilesetResolver,
  HandLandmarker,
  type FaceLandmarkerResult,
  type HandLandmarkerResult
} from "@mediapipe/tasks-vision";
import { extractMetrics, summarizeHands, summarizeLandmarks } from "./landmark-math";

const FACE_MODEL =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
const HAND_MODEL =
  "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";
const WASM_BASE = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.34/wasm";

export interface ObservationSnapshot {
  landmarks: number[][];
  hand_landmarks: number[][][];
  client_metrics: Record<string, number | boolean | string | null>;
  frame_b64?: string;
}

export function useBiometricCapture() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRequestRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const faceRef = useRef<FaceLandmarker | null>(null);
  const handRef = useRef<HandLandmarker | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [lastSnapshot, setLastSnapshot] = useState<ObservationSnapshot>({
    landmarks: [],
    hand_landmarks: [],
    client_metrics: { face_present: false }
  });

  useEffect(() => {
    let cancelled = false;

    async function waitForVideoRef(maxWaitMs = 3000): Promise<HTMLVideoElement> {
      const start = Date.now();
      while (!videoRef.current && Date.now() - start < maxWaitMs) {
        await new Promise((r) => setTimeout(r, 50));
      }
      if (!videoRef.current) {
        throw new Error("Video element not available");
      }
      return videoRef.current;
    }

    async function startCamera(): Promise<MediaStream> {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: "user"
        },
        audio: false
      });
      streamRef.current = stream;

      const video = await waitForVideoRef();
      video.srcObject = stream;
      await video.play();
      return stream;
    }

    async function loadModels() {
      const vision = await FilesetResolver.forVisionTasks(WASM_BASE);

      // Try GPU first, fall back to CPU if unavailable
      async function createFace(delegate: "GPU" | "CPU") {
        return FaceLandmarker.createFromOptions(vision, {
          baseOptions: { modelAssetPath: FACE_MODEL, delegate },
          runningMode: "VIDEO",
          numFaces: 1,
          outputFaceBlendshapes: true
        });
      }

      async function createHand(delegate: "GPU" | "CPU") {
        return HandLandmarker.createFromOptions(vision, {
          baseOptions: { modelAssetPath: HAND_MODEL, delegate },
          runningMode: "VIDEO",
          numHands: 2
        });
      }

      let faceLandmarker: FaceLandmarker;
      let handLandmarker: HandLandmarker;

      try {
        [faceLandmarker, handLandmarker] = await Promise.all([
          createFace("GPU"),
          createHand("GPU")
        ]);
      } catch {
        // GPU delegate failed — retry with CPU
        [faceLandmarker, handLandmarker] = await Promise.all([
          createFace("CPU"),
          createHand("CPU")
        ]);
      }

      return { faceLandmarker, handLandmarker };
    }

    async function initialize() {
      // --- Step 1: Camera ---
      try {
        await startCamera();
      } catch (camErr) {
        const msg = camErr instanceof Error ? camErr.message : String(camErr);
        console.error("Camera error:", camErr);
        setError(`Camera error: ${msg}`);
        setLoading(false);
        return; // No point loading models without a camera
      }

      if (cancelled) { setLoading(false); return; }

      // --- Step 2: MediaPipe models ---
      try {
        const { faceLandmarker, handLandmarker } = await loadModels();

        if (cancelled) {
          faceLandmarker.close();
          handLandmarker.close();
          setLoading(false);
          return;
        }

        faceRef.current = faceLandmarker;
        handRef.current = handLandmarker;
        setReady(true);
        setError(null);
      } catch (modelErr) {
        // Camera is working — only model loading failed
        console.error("Model loading error:", modelErr);
        const msg = modelErr instanceof Error ? modelErr.message : String(modelErr);
        setError(`Model loading failed: ${msg}`);
      } finally {
        setLoading(false);
      }
    }

    initialize();

    return () => {
      cancelled = true;
      if (frameRequestRef.current) {
        cancelAnimationFrame(frameRequestRef.current);
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
      faceRef.current?.close();
      handRef.current?.close();
    };
  }, []);

  useEffect(() => {
    if (!ready || !videoRef.current || !faceRef.current || !handRef.current) {
      return;
    }

    const loop = () => {
      const video = videoRef.current;
      if (!video || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
        frameRequestRef.current = requestAnimationFrame(loop);
        return;
      }

      const now = performance.now();
      const faceResult = faceRef.current?.detectForVideo(video, now) as FaceLandmarkerResult | undefined;
      const handResult = handRef.current?.detectForVideo(video, now) as HandLandmarkerResult | undefined;
      const faceLandmarks = faceResult?.faceLandmarks?.[0] ?? [];
      const hands = handResult?.landmarks ?? [];
      const metrics = extractMetrics(faceLandmarks, hands);

      setLastSnapshot({
        landmarks: summarizeLandmarks(faceLandmarks),
        hand_landmarks: summarizeHands(hands),
        client_metrics: metrics
      });

      frameRequestRef.current = requestAnimationFrame(loop);
    };

    frameRequestRef.current = requestAnimationFrame(loop);

    return () => {
      if (frameRequestRef.current) {
        cancelAnimationFrame(frameRequestRef.current);
      }
    };
  }, [ready]);

  const captureSnapshot = useMemo(
    () => () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas) {
        return lastSnapshot;
      }

      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
      const context = canvas.getContext("2d");
      context?.drawImage(video, 0, 0, canvas.width, canvas.height);

      return {
        ...lastSnapshot,
        frame_b64: canvas.toDataURL("image/jpeg", 0.82)
      };
    },
    [lastSnapshot]
  );

  return {
    videoRef,
    canvasRef,
    loading,
    error,
    ready,
    snapshot: lastSnapshot,
    captureSnapshot
  };
}
