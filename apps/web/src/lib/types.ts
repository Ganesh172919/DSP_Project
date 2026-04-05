export type VerificationStage =
  | "face_detection"
  | "presentation_attack_detection"
  | "recognition"
  | "feature_verification"
  | "liveness"
  | "deepfake_scan"
  | "decision";

export interface StageResult {
  stage: VerificationStage;
  label?: string;
  score: number;
  passed: boolean;
  message: string;
  weight?: number;
  threshold?: number;
}

export interface LiveChallengeTelemetry {
  id: string;
  title: string;
  frames_processed: number;
  progress: number;
  status: string;
  score?: number | null;
  passed?: boolean | null;
  message: string;
}

export interface LiveProcessingTelemetry {
  processed_frames: number;
  processed_challenges: number;
  total_challenges: number;
  liveness_preview_score: number;
  current_challenge_id?: string | null;
  current_challenge_title?: string | null;
  current_challenge_frames: number;
  current_challenge_progress: number;
  current_challenge_score?: number | null;
  current_challenge_passed?: boolean | null;
  current_challenge_message: string;
  processing_time_ms: number;
  capture_age_ms?: number | null;
  quality_score: number;
  pad_score: number;
  deepfake_score: number;
  frame_analysis_available: boolean;
  provisional_risk: boolean;
  guidance: string[];
  challenge_results: LiveChallengeTelemetry[];
}

export interface ChallengeDefinition {
  id: string;
  title: string;
  description: string;
  category: string;
  duration_seconds: number;
}

export interface RegistrationStartResponse {
  session_id: string;
  expires_at: string;
}

export interface RegistrationCaptureRequest {
  step: string;
  frame_b64?: string;
  landmarks: number[][];
  hand_landmarks?: number[][][];
  client_metrics: Record<string, number | boolean | string | null>;
  captured_at: string;
}

export interface AuthenticationStartResponse {
  attempt_id: string;
  challenges: ChallengeDefinition[];
  attempt_number?: number;
  max_attempts?: number;
}

export interface AuthenticationFrameRequest extends RegistrationCaptureRequest {
  challenge_id?: string;
}

export interface AuthenticationStateResponse {
  attempt_id: string;
  stage_results: StageResult[];
  final_score?: number;
  authenticated?: boolean;
  anomalies: string[];
  denial_reasons: string[];
  needs_review?: boolean;
  attempts_remaining?: number;
  live_telemetry?: LiveProcessingTelemetry | null;
}

export interface DashboardMetrics {
  total_authentications: number;
  success_rate: number;
  blocked_attacks: number;
  average_latency_ms: number;
  active_alerts: number;
  recent_events: Array<{
    id: string;
    event_type: string;
    severity: string;
    occurred_at: string;
    message: string;
  }>;
  challenge_success_rates?: Record<string, number>;
  attack_type_counts?: Record<string, number>;
}
