"use client";

import { AlertTriangle, ArrowLeft, FileText, Library, Loader2, SearchX, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { AnswerContent } from "@/components/chat/answer-content";
import { Composer } from "@/components/chat/composer";
import { SourcesList } from "@/components/chat/sources-list";
import { EmptyState } from "@/components/layout/empty-state";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Logo } from "@/components/ui/logo";
import { Skeleton } from "@/components/ui/skeleton";
import { useChatStream, useConversation, useDeleteConversation } from "@/hooks/use-conversations";
import { useDocuments } from "@/hooks/use-documents";
import { NO_ANSWER } from "@/lib/constants";
import type { ChatMessage } from "@/types/api";

const SUGGESTIONS = [
  "Resuma os pontos principais do documento.",
  "Quais são os prazos e datas importantes?",
  "Quais obrigações e responsabilidades são definidas?",
];

function AssistantAvatar() {
  return (
    <div className="mt-0.5 shrink-0" aria-hidden>
      <Logo withText={false} className="[&_svg]:size-7" />
    </div>
  );
}

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end animate-fade-in">
      <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-accent px-4 py-2.5 text-[15px] leading-relaxed text-accent-fg">
        {content}
      </div>
    </div>
  );
}

function AssistantMessage({ message }: { message: ChatMessage }) {
  const [activeRank, setActiveRank] = useState<number | null>(null);
  const ranks = useMemo(() => new Set(message.citations.map((c) => c.rank)), [message.citations]);
  const abstained = message.content.trim() === NO_ANSWER;
  const ungrounded = !abstained && message.citations.length === 0;

  function cite(rank: number) {
    setActiveRank(rank);
    document
      .getElementById(`source-${message.id}-${rank}`)
      ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    window.setTimeout(() => setActiveRank((current) => (current === rank ? null : current)), 2200);
  }

  return (
    <div className="flex gap-3 animate-fade-in">
      <AssistantAvatar />
      <div className="min-w-0 flex-1 pt-0.5">
        {abstained ? (
          <div className="flex items-start gap-2.5 rounded-lg border border-border bg-surface-2/60 px-4 py-3 text-sm text-fg-muted">
            <SearchX className="mt-0.5 size-4 shrink-0" />
            <div>
              <p className="font-medium text-fg">{NO_ANSWER}</p>
              <p className="mt-0.5 text-xs">
                Nenhum trecho relevante foi encontrado. Tente reformular a pergunta ou incluir outros documentos.
              </p>
            </div>
          </div>
        ) : (
          <AnswerContent content={message.content} ranks={ranks} onCite={cite} />
        )}
        {ungrounded && (
          <p className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-warning/10 px-2 py-1 text-xs text-warning">
            <AlertTriangle className="size-3.5" /> Resposta sem citações: confira a informação nos documentos.
          </p>
        )}
        <SourcesList messageId={message.id} citations={message.citations} activeRank={activeRank} />
      </div>
    </div>
  );
}

function StreamingMessage({ draft, stage }: { draft: string; stage: "idle" | "retrieving" | "generating" }) {
  return (
    <div className="flex gap-3" aria-live="polite" aria-busy>
      <AssistantAvatar />
      <div className="min-w-0 flex-1 pt-0.5">
        {draft ? (
          <div className="[&_p:last-child]:after:ml-0.5 [&_p:last-child]:after:inline-block [&_p:last-child]:after:h-4 [&_p:last-child]:after:w-1.5 [&_p:last-child]:after:translate-y-0.5 [&_p:last-child]:after:animate-pulse [&_p:last-child]:after:bg-accent [&_p:last-child]:after:content-['']">
            <AnswerContent content={draft} />
          </div>
        ) : (
          <p className="flex items-center gap-2 py-1 text-sm text-fg-muted">
            <Loader2 className="size-4 animate-spin text-accent" />
            {stage === "generating" ? "Escrevendo a resposta…" : "Buscando trechos relevantes nos documentos…"}
          </p>
        )}
      </div>
    </div>
  );
}

export function ChatThread() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const router = useRouter();
  const conversation = useConversation(conversationId);
  const documents = useDocuments();
  const stream = useChatStream(conversationId);
  const remove = useDeleteConversation();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const messages = conversation.data?.messages ?? [];
  const docTitles = useMemo(
    () => new Map((documents.data ?? []).map((d) => [d.id, d.title])),
    [documents.data],
  );

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages.length, stream.draft, stream.pendingQuestion]);

  if (conversation.isPending) {
    return (
      <div className="flex flex-1 flex-col gap-6 p-6" aria-busy>
        <Skeleton className="h-6 w-1/3" />
        <Skeleton className="ml-auto h-10 w-1/2 rounded-2xl" />
        <Skeleton className="h-24 w-3/4" />
      </div>
    );
  }
  if (conversation.isError) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <EmptyState
          icon={SearchX}
          title="Conversa não encontrada"
          description={conversation.error.message}
          action={
            <Button asChild variant="secondary">
              <Link href="/chat">Voltar às conversas</Link>
            </Button>
          }
        />
      </div>
    );
  }

  const data = conversation.data;
  const empty = messages.length === 0 && !stream.pendingQuestion;

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <header className="flex items-center gap-2 border-b border-border px-4 py-3 sm:px-6">
        <Button asChild variant="ghost" size="icon" className="md:hidden" aria-label="Voltar às conversas">
          <Link href="/chat">
            <ArrowLeft />
          </Link>
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-sm font-semibold">{data.title}</h1>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {data.document_ids.length === 0 ? (
              <span className="inline-flex items-center gap-1 text-xs text-fg-subtle">
                <Library className="size-3.5" /> Toda a biblioteca
              </span>
            ) : (
              data.document_ids.map((id) => (
                <Link
                  key={id}
                  href={`/documents/${id}`}
                  className="inline-flex max-w-[220px] items-center gap-1 rounded-full border border-border px-2 py-0.5 text-xs text-fg-muted hover:border-border-strong hover:text-fg"
                >
                  <FileText className="size-3 shrink-0" />
                  <span className="truncate">{docTitles.get(id) ?? "Documento"}</span>
                </Link>
              ))
            )}
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Excluir conversa"
          title="Excluir conversa"
          className="hover:text-danger"
          onClick={() => setConfirmDelete(true)}
        >
          <Trash2 />
        </Button>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6 sm:px-6">
          {empty && (
            <div className="py-10 text-center animate-rise">
              <h2 className="text-lg font-semibold">O que você quer saber?</h2>
              <p className="mt-1 text-sm text-fg-muted">
                As respostas usam apenas o conteúdo dos documentos desta conversa.
              </p>
              <div className="mt-6 flex flex-col items-stretch gap-2 sm:items-center">
                {SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => stream.send(suggestion)}
                    className="rounded-lg border border-border bg-surface px-4 py-2.5 text-sm text-fg-muted transition-colors hover:border-accent/50 hover:text-fg"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) =>
            message.role === "user" ? (
              <UserBubble key={message.id} content={message.content} />
            ) : (
              <AssistantMessage key={message.id} message={message} />
            ),
          )}

          {stream.pendingQuestion && (
            <>
              <UserBubble content={stream.pendingQuestion} />
              <StreamingMessage draft={stream.draft} stage={stream.stage} />
            </>
          )}

          {stream.error && (
            <Alert tone="danger" title="Não foi possível concluir a resposta">
              <span>{stream.error}</span>
              <span className="mt-2 flex gap-2">
                {stream.failedQuestion && (
                  <Button size="sm" variant="secondary" onClick={() => stream.send(stream.failedQuestion!)}>
                    Tentar novamente
                  </Button>
                )}
                <Button size="sm" variant="ghost" onClick={stream.dismissError}>
                  Dispensar
                </Button>
              </span>
            </Alert>
          )}
        </div>
      </div>

      <div className="border-t border-border bg-bg/80 px-4 py-3 backdrop-blur sm:px-6">
        <div className="mx-auto max-w-3xl">
          <Composer onSend={stream.send} onStop={stream.stop} streaming={stream.streaming} />
        </div>
      </div>

      <Dialog
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Excluir conversa?"
        description="O histórico desta conversa será apagado. Os documentos não são afetados."
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(false)}>
              Cancelar
            </Button>
            <Button
              variant="danger"
              loading={remove.isPending}
              onClick={() =>
                remove.mutate(conversationId, {
                  onSuccess: () => {
                    toast.success("Conversa excluída.");
                    router.push("/chat");
                  },
                  onError: (error) => toast.error(error.message),
                })
              }
            >
              Excluir
            </Button>
          </>
        }
      />
    </div>
  );
}
