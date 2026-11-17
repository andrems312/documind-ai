"use client";

import { MessageSquarePlus, MessagesSquare } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { NewConversationDialog } from "@/components/chat/new-conversation-dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useConversations } from "@/hooks/use-conversations";
import { cn } from "@/lib/utils/cn";
import { formatRelative } from "@/lib/utils/format";

function ConversationList({ onNew }: { onNew: () => void }) {
  const pathname = usePathname();
  const conversations = useConversations();

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-2 px-4 py-3">
        <h2 className="text-sm font-semibold">Conversas</h2>
        <Button size="sm" onClick={onNew}>
          <MessageSquarePlus /> Nova
        </Button>
      </div>
      <nav aria-label="Conversas" className="flex-1 overflow-y-auto scrollbar-thin px-2 pb-3">
        {conversations.isPending ? (
          <div className="space-y-2 px-2" aria-busy>
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-12" />
            ))}
          </div>
        ) : conversations.isError ? (
          <p className="px-2 text-xs text-danger">{conversations.error.message}</p>
        ) : conversations.data.length === 0 ? (
          <p className="px-3 py-6 text-center text-xs text-fg-subtle">Nenhuma conversa ainda.</p>
        ) : (
          <ul className="space-y-0.5">
            {conversations.data.map((conversation) => {
              const href = `/chat/${conversation.id}`;
              const active = pathname === href;
              return (
                <li key={conversation.id}>
                  <Link
                    href={href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "block rounded-md px-3 py-2 transition-colors",
                      active ? "bg-accent-soft" : "hover:bg-surface-2",
                    )}
                  >
                    <span className={cn("block truncate text-sm", active ? "font-medium text-accent" : "text-fg")}>
                      {conversation.title}
                    </span>
                    <span className="block text-xs text-fg-subtle">
                      {formatRelative(conversation.updated_at)} ·{" "}
                      {conversation.document_ids.length === 0
                        ? "toda a biblioteca"
                        : `${conversation.document_ids.length} doc.`}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </nav>
    </div>
  );
}

/** Layout do chat: lista de conversas + conversa aberta. No celular, mostra um de cada vez. */
export function ChatShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [dialogOpen, setDialogOpen] = useState(false);
  const inConversation = pathname !== "/chat";

  return (
    <div className="-mx-4 -my-6 flex h-[calc(100dvh-4rem)] sm:-mx-6 lg:-mx-8">
      <aside
        className={cn(
          "w-full shrink-0 border-r border-border bg-surface md:w-72",
          inConversation ? "hidden md:block" : "block",
        )}
      >
        <ConversationList onNew={() => setDialogOpen(true)} />
      </aside>
      <section className={cn("min-w-0 flex-1", inConversation ? "flex" : "hidden md:flex")}>
        {children}
      </section>
      <NewConversationDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </div>
  );
}

export function ChatIndex() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center p-8 text-center animate-rise">
      <div className="relative mb-4">
        <div className="absolute inset-0 rounded-full bg-accent/20 blur-xl" aria-hidden />
        <div className="relative flex size-14 items-center justify-center rounded-2xl border border-border bg-surface shadow-card">
          <MessagesSquare className="size-6 text-accent" aria-hidden />
        </div>
      </div>
      <h1 className="text-lg font-semibold">Converse com seus documentos</h1>
      <p className="mt-1 max-w-sm text-sm text-fg-muted">
        Abra uma conversa à esquerda ou crie uma nova. As respostas citam a página de onde cada informação foi
        tirada.
      </p>
    </div>
  );
}
