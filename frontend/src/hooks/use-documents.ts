"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, apiUpload } from "@/lib/api/client";
import type { DocumentItem, DocumentPage } from "@/types/api";

export const documentsKey = ["documents"] as const;
export const documentKey = (id: string) => ["documents", id] as const;

const isPending = (d: DocumentItem) => d.status === "uploaded" || d.status === "processing";

/** Lista de documentos; consulta a cada 2s enquanto houver algum em processamento. */
export function useDocuments() {
  return useQuery({
    queryKey: documentsKey,
    queryFn: () => apiFetch<DocumentItem[]>("/api/v1/documents"),
    refetchInterval: (query) => (query.state.data?.some(isPending) ? 2000 : false),
  });
}

export function useDocument(id: string) {
  return useQuery({
    queryKey: documentKey(id),
    queryFn: () => apiFetch<DocumentItem>(`/api/v1/documents/${id}`),
    refetchInterval: (query) => (query.state.data && isPending(query.state.data) ? 2000 : false),
  });
}

export function useDocumentPage(id: string, page: number, enabled: boolean) {
  return useQuery({
    queryKey: ["documents", id, "pages", page],
    queryFn: () => apiFetch<DocumentPage>(`/api/v1/documents/${id}/pages/${page}`),
    enabled,
    staleTime: Number.POSITIVE_INFINITY,
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ file, onProgress }: { file: File; onProgress?: (p: number) => void }) =>
      apiUpload<DocumentItem>("/api/v1/documents", file, onProgress),
    onSuccess: (document) => {
      queryClient.setQueryData<DocumentItem[]>(documentsKey, (old) => [document, ...(old ?? [])]);
      void queryClient.invalidateQueries({ queryKey: documentsKey });
    },
  });
}

export function useRenameDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      apiFetch<DocumentItem>(`/api/v1/documents/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      }),
    onSuccess: (document) => {
      queryClient.setQueryData(documentKey(document.id), document);
      void queryClient.invalidateQueries({ queryKey: documentsKey });
    },
  });
}

export function useReprocessDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<DocumentItem>(`/api/v1/documents/${id}/reprocess`, { method: "POST" }),
    onSuccess: (document) => {
      queryClient.setQueryData(documentKey(document.id), document);
      void queryClient.invalidateQueries({ queryKey: documentsKey });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/api/v1/documents/${id}`, { method: "DELETE" }),
    onSuccess: (_, id) => {
      queryClient.setQueryData<DocumentItem[]>(documentsKey, (old) => old?.filter((d) => d.id !== id));
      queryClient.removeQueries({ queryKey: documentKey(id) });
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}
