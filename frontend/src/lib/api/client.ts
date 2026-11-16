"use client";

import { createClient } from "@/lib/supabase/client";
import { env } from "@/lib/env";
import type { ApiErrorBody } from "@/types/api";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function accessToken(): Promise<string | null> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

/**
 * Chamada tipada ao backend. Anexa o token do Supabase como Bearer e converte o envelope de
 * erro da API (`{ error: { code, message } }`) em `ApiError`.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = await accessToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${env.apiUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "network_error", "Não foi possível conectar à API.");
  }

  if (!response.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      // corpo não-JSON (ex.: proxy)
    }
    throw new ApiError(
      response.status,
      body?.error.code ?? "http_error",
      body?.error.message ?? `Erro ${response.status} ao chamar a API.`,
      body?.error.details,
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
