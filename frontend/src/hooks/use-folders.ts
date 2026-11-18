"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type { DocumentItem, Folder } from "@/types/api";
import { documentsKey, documentKey } from "@/hooks/use-documents";

export const foldersKey = ["folders"] as const;

export function useFolders() {
  return useQuery({
    queryKey: foldersKey,
    queryFn: () => apiFetch<Folder[]>("/api/v1/folders"),
  });
}

export function useCreateFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string; color?: string | null }) =>
      apiFetch<Folder>("/api/v1/folders", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: foldersKey }),
  });
}

export function useUpdateFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...input }: { id: string; name?: string; color?: string | null }) =>
      apiFetch<Folder>(`/api/v1/folders/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: foldersKey }),
  });
}

export function useDeleteFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/api/v1/folders/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: foldersKey });
      void queryClient.invalidateQueries({ queryKey: documentsKey });
    },
  });
}

/** Move (ou remove de) uma pasta: PATCH /documents/{id} com folder_id. */
export function useMoveDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, folderId }: { id: string; folderId: string | null }) =>
      apiFetch<DocumentItem>(`/api/v1/documents/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ folder_id: folderId }),
      }),
    onSuccess: (document) => {
      queryClient.setQueryData(documentKey(document.id), document);
      void queryClient.invalidateQueries({ queryKey: documentsKey });
      void queryClient.invalidateQueries({ queryKey: foldersKey });
    },
  });
}
