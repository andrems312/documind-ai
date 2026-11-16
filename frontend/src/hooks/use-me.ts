"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type { HealthResponse, Profile } from "@/types/api";

export const meQueryKey = ["me"] as const;

/** Perfil do usuário autenticado, lido do backend (cria o perfil no primeiro acesso). */
export function useMe() {
  return useQuery({
    queryKey: meQueryKey,
    queryFn: () => apiFetch<Profile>("/api/v1/me"),
    staleTime: 5 * 60 * 1000,
  });
}

/** Status da API e de suas dependências. */
export function useApiHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<HealthResponse>("/api/v1/health"),
    refetchInterval: 60 * 1000,
    retry: 1,
  });
}
