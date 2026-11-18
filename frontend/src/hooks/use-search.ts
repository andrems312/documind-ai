"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type { SearchResponse } from "@/types/api";

export function useSearch(query: string, folderId: string | null) {
  const trimmed = query.trim();
  return useQuery({
    queryKey: ["search", trimmed, folderId],
    queryFn: () => {
      const params = new URLSearchParams({ q: trimmed });
      if (folderId) params.set("folder_id", folderId);
      return apiFetch<SearchResponse>(`/api/v1/search?${params.toString()}`);
    },
    enabled: trimmed.length >= 2,
    staleTime: 60 * 1000,
  });
}
