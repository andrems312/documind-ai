/** Tipos espelhando os schemas Pydantic do backend (app/schemas). */

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  environment: string;
  checks: Record<string, string>;
}

export interface Profile {
  id: string;
  email: string | null;
  full_name: string | null;
  avatar_url: string | null;
  created_at: string;
}

export interface ProfileUpdate {
  full_name?: string;
  avatar_url?: string | null;
}
