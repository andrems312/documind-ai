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

async function authHeaders(init?: HeadersInit): Promise<Headers> {
  const headers = new Headers(init);
  const token = await accessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return headers;
}

function errorFromBody(status: number, body: ApiErrorBody | null): ApiError {
  return new ApiError(
    status,
    body?.error.code ?? "http_error",
    body?.error.message ?? `Erro ${status} ao chamar a API.`,
    body?.error.details,
  );
}

async function parseError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody | null = null;
  try {
    body = (await response.json()) as ApiErrorBody;
  } catch {
    // corpo não-JSON (ex.: proxy)
  }
  return errorFromBody(response.status, body);
}

async function rawFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = await authHeaders(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch(`${env.apiUrl}${path}`, { ...init, headers });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, "network_error", "Não foi possível conectar à API.");
  }
  if (!response.ok) throw await parseError(response);
  return response;
}

/**
 * Chamada tipada ao backend. Anexa o token do Supabase como Bearer e converte o envelope de
 * erro da API (`{ error: { code, message } }`) em `ApiError`.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await rawFetch(path, init);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Abre uma resposta em streaming (SSE). O chamador lê `response.body`. */
export async function apiStream(path: string, body: unknown, signal?: AbortSignal) {
  return rawFetch(path, {
    method: "POST",
    body: JSON.stringify(body),
    headers: { Accept: "text/event-stream" },
    signal,
  });
}

/** Baixa um arquivo autenticado como Blob (ex.: PDF original). */
export async function apiBlob(path: string): Promise<Blob> {
  return (await rawFetch(path)).blob();
}

/**
 * Upload multipart com progresso. Usa XMLHttpRequest porque `fetch` ainda não expõe o
 * progresso de envio de forma portável entre navegadores.
 */
export async function apiUpload<T>(
  path: string,
  file: File,
  onProgress?: (fraction: number) => void,
): Promise<T> {
  const token = await accessToken();
  const form = new FormData();
  form.append("file", file);

  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${env.apiUrl}${path}`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(event.loaded / event.total);
    };
    xhr.onerror = () => reject(new ApiError(0, "network_error", "Não foi possível conectar à API."));
    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = xhr.responseText ? JSON.parse(xhr.responseText) : null;
      } catch {
        body = null;
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as T);
      else reject(errorFromBody(xhr.status, body as ApiErrorBody | null));
    };
    xhr.send(form);
  });
}
