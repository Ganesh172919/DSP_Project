import type {
  AuthenticationFrameRequest,
  AuthenticationStartResponse,
  AuthenticationStateResponse,
  DashboardMetrics,
  RegistrationCaptureRequest,
  RegistrationStartResponse
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    ...init
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function startRegistration(payload: {
  email: string;
  password: string;
  full_name: string;
  accessibility_profile?: Record<string, boolean>;
}) {
  return request<RegistrationStartResponse>("/registration/start", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function submitRegistrationFrame(sessionId: string, payload: RegistrationCaptureRequest) {
  return request<{ accepted: boolean; quality_score: number; guidance: string[] }>(
    `/registration/${sessionId}/frame`,
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export function completeRegistration(sessionId: string) {
  return request<{ user_id: string; quality_score: number; security_score: number }>(
    `/registration/${sessionId}/complete`,
    {
      method: "POST"
    }
  );
}

export function startAuthentication(payload: { email: string }) {
  return request<AuthenticationStartResponse>("/authentication/start", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function submitAuthenticationFrame(attemptId: string, payload: AuthenticationFrameRequest) {
  return request<AuthenticationStateResponse>(`/authentication/${attemptId}/frame`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function completeAuthentication(attemptId: string) {
  return request<AuthenticationStateResponse>(`/authentication/${attemptId}/complete`, {
    method: "POST"
  });
}

export function fetchDashboardMetrics() {
  return request<DashboardMetrics>("/admin/metrics");
}

export function fetchProfile(email: string) {
  return request<{
    full_name: string;
    email: string;
    registration_completed: boolean;
    template_quality_score: number;
    security_score: number;
    recent_attempts: Array<{
      id: string;
      status: string;
      final_score: number;
      created_at: string;
    }>;
  }>(`/users/profile?email=${encodeURIComponent(email)}`);
}

