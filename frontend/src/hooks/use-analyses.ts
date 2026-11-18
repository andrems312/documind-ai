"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { statsKey } from "@/hooks/use-stats";
import type { Analysis, AnalysisListItem, AnalysisType } from "@/types/api";

export const analysesKey = ["analyses"] as const;
export const analysisKey = (id: string) => ["analyses", id] as const;

const ENDPOINT: Record<AnalysisType, string> = {
  summary: "/api/v1/analyses/summary",
  key_info: "/api/v1/analyses/key-info",
  comparison: "/api/v1/analyses/comparison",
};

export function useAnalyses() {
  return useQuery({
    queryKey: analysesKey,
    queryFn: () => apiFetch<AnalysisListItem[]>("/api/v1/analyses"),
  });
}

export function useAnalysis(id: string, enabled = true) {
  return useQuery({
    queryKey: analysisKey(id),
    queryFn: () => apiFetch<Analysis>(`/api/v1/analyses/${id}`),
    enabled,
    staleTime: Number.POSITIVE_INFINITY,
  });
}

export function useGenerateAnalysis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ type, documentIds }: { type: AnalysisType; documentIds: string[] }) =>
      apiFetch<Analysis>(ENDPOINT[type], {
        method: "POST",
        body: JSON.stringify({ document_ids: documentIds }),
      }),
    onSuccess: (analysis) => {
      queryClient.setQueryData(analysisKey(analysis.id), analysis);
      void queryClient.invalidateQueries({ queryKey: analysesKey });
      void queryClient.invalidateQueries({ queryKey: statsKey });
    },
  });
}

export function useDeleteAnalysis() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/api/v1/analyses/${id}`, { method: "DELETE" }),
    onSuccess: (_, id) => {
      queryClient.removeQueries({ queryKey: analysisKey(id) });
      void queryClient.invalidateQueries({ queryKey: analysesKey });
      void queryClient.invalidateQueries({ queryKey: statsKey });
    },
  });
}
