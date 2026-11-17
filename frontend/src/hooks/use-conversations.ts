"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, apiFetch, apiStream } from "@/lib/api/client";
import { readSSE } from "@/lib/api/sse";
import type { ChatStreamEvent, Conversation, ConversationDetail } from "@/types/api";

export const conversationsKey = ["conversations"] as const;
export const conversationKey = (id: string) => ["conversations", id] as const;

export function useConversations() {
  return useQuery({
    queryKey: conversationsKey,
    queryFn: () => apiFetch<Conversation[]>("/api/v1/conversations"),
  });
}

export function useConversation(id: string) {
  return useQuery({
    queryKey: conversationKey(id),
    queryFn: () => apiFetch<ConversationDetail>(`/api/v1/conversations/${id}`),
  });
}

export function useCreateConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { document_ids: string[]; title?: string }) =>
      apiFetch<Conversation>("/api/v1/conversations", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: (conversation) => {
      queryClient.setQueryData<Conversation[]>(conversationsKey, (old) => [
        conversation,
        ...(old ?? []),
      ]);
    },
  });
}

export function useRenameConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) =>
      apiFetch<Conversation>(`/api/v1/conversations/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: conversationsKey }),
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/api/v1/conversations/${id}`, { method: "DELETE" }),
    onSuccess: (_, id) => {
      queryClient.setQueryData<Conversation[]>(conversationsKey, (old) =>
        old?.filter((c) => c.id !== id),
      );
      queryClient.removeQueries({ queryKey: conversationKey(id) });
    },
  });
}

export type StreamStage = "idle" | "retrieving" | "generating";

export interface ChatStreamState {
  /** Pergunta enviada que ainda não voltou do servidor. */
  pendingQuestion: string | null;
  /** Texto parcial da resposta recebido em streaming. */
  draft: string;
  stage: StreamStage;
  error: string | null;
  /** Pergunta cuja resposta falhou, para o botão "Tentar novamente". */
  failedQuestion: string | null;
  streaming: boolean;
}

const idle: ChatStreamState = {
  pendingQuestion: null,
  draft: "",
  stage: "idle",
  error: null,
  failedQuestion: null,
  streaming: false,
};

/** Envia perguntas e acompanha a resposta em streaming (SSE) de uma conversa. */
export function useChatStream(conversationId: string) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<ChatStreamState>(idle);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => () => controller.current?.abort(), []);

  const send = useCallback(
    async (question: string) => {
      controller.current?.abort();
      const abort = new AbortController();
      controller.current = abort;
      setState({ ...idle, pendingQuestion: question, streaming: true, stage: "retrieving" });

      try {
        const response = await apiStream(
          `/api/v1/conversations/${conversationId}/messages`,
          { content: question },
          abort.signal,
        );
        if (!response.body) throw new ApiError(0, "stream_error", "Resposta sem conteúdo.");

        for await (const event of readSSE<ChatStreamEvent>(response.body)) {
          if (event.type === "status") {
            setState((s) => ({ ...s, stage: event.stage }));
          } else if (event.type === "token") {
            setState((s) => ({ ...s, stage: "generating", draft: s.draft + event.delta }));
          } else if (event.type === "error") {
            setState((s) => ({ ...s, error: event.message }));
          }
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") {
          setState((s) => ({ ...s, error: "Resposta interrompida." }));
        } else {
          const message = error instanceof Error ? error.message : "Falha ao enviar a pergunta.";
          setState((s) => ({ ...s, error: message }));
        }
      } finally {
        // O servidor já persistiu pergunta e resposta: recarrega o histórico oficial.
        await queryClient.invalidateQueries({ queryKey: conversationKey(conversationId) });
        void queryClient.invalidateQueries({ queryKey: conversationsKey });
        setState((s) => ({
          ...idle,
          error: s.error,
          failedQuestion: s.error ? s.pendingQuestion : null,
        }));
        if (controller.current === abort) controller.current = null;
      }
    },
    [conversationId, queryClient],
  );

  const stop = useCallback(() => controller.current?.abort(), []);
  const dismissError = useCallback(() => setState(idle), []);

  return { ...state, send, stop, dismissError };
}
