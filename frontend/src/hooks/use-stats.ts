"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type { StatsOverview } from "@/types/api";

export const statsKey = ["stats", "overview"] as const;

export function useStats() {
  return useQuery({
    queryKey: statsKey,
    queryFn: () => apiFetch<StatsOverview>("/api/v1/stats/overview"),
    staleTime: 30 * 1000,
  });
}
