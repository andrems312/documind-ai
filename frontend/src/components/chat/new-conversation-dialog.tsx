"use client";

import { FileText, Library } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useCreateConversation } from "@/hooks/use-conversations";
import { useDocuments } from "@/hooks/use-documents";
import { cn } from "@/lib/utils/cn";
import { pluralize } from "@/lib/utils/format";

export function NewConversationDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const documents = useDocuments();
  const create = useCreateConversation();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const ready = (documents.data ?? []).filter((d) => d.status === "ready");

  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function submit() {
    try {
      const conversation = await create.mutateAsync({ document_ids: [...selected] });
      setSelected(new Set());
      onClose();
      router.push(`/chat/${conversation.id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível criar a conversa.");
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Nova conversa"
      description="Escolha os documentos que a IA pode consultar. Sem seleção, ela consulta toda a sua biblioteca."
      footer={
        ready.length > 0 && (
          <>
            <Button variant="secondary" onClick={onClose}>
              Cancelar
            </Button>
            <Button onClick={submit} loading={create.isPending}>
              {selected.size === 0
                ? "Usar toda a biblioteca"
                : `Conversar com ${pluralize(selected.size, "documento", "documentos")}`}
            </Button>
          </>
        )
      }
    >
      {documents.isPending ? (
        <div className="space-y-2">
          <Skeleton className="h-11" />
          <Skeleton className="h-11" />
        </div>
      ) : ready.length === 0 ? (
        <div className="rounded-md border border-dashed border-border-strong p-6 text-center">
          <p className="text-sm text-fg-muted">Você ainda não tem documentos prontos para consulta.</p>
          <Button asChild size="sm" className="mt-4" onClick={onClose}>
            <Link href="/documents">Enviar um PDF</Link>
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-2 text-xs",
              selected.size === 0 ? "bg-accent-soft text-accent" : "bg-surface-2 text-fg-muted",
            )}
          >
            <Library className="size-4" />
            {selected.size === 0
              ? `Toda a biblioteca (${pluralize(ready.length, "documento", "documentos")})`
              : `${pluralize(selected.size, "documento selecionado", "documentos selecionados")}`}
          </div>
          <ul className="max-h-72 space-y-1.5 overflow-y-auto scrollbar-thin pr-1">
            {ready.map((document) => {
              const checked = selected.has(document.id);
              return (
                <li key={document.id}>
                  <label
                    className={cn(
                      "flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2.5 text-sm transition-colors",
                      checked ? "border-accent bg-accent-soft/60" : "border-border hover:bg-surface-2",
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(document.id)}
                      className="size-4 accent-[var(--accent)]"
                    />
                    <FileText className="size-4 shrink-0 text-fg-subtle" />
                    <span className="min-w-0 flex-1 truncate">{document.title}</span>
                    <span className="shrink-0 text-xs text-fg-subtle">
                      {pluralize(document.page_count ?? 0, "pág.", "págs.")}
                    </span>
                  </label>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </Dialog>
  );
}
