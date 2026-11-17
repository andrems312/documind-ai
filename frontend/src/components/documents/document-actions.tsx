"use client";

import { MessageSquarePlus, Pencil, RotateCw, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useCreateConversation } from "@/hooks/use-conversations";
import { useDeleteDocument, useRenameDocument, useReprocessDocument } from "@/hooks/use-documents";
import type { DocumentItem } from "@/types/api";

/** Cria uma conversa sobre um único documento e navega até ela. */
export function useStartChat() {
  const router = useRouter();
  const create = useCreateConversation();
  return {
    pending: create.isPending,
    start: async (document: DocumentItem) => {
      try {
        const conversation = await create.mutateAsync({ document_ids: [document.id] });
        router.push(`/chat/${conversation.id}`);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Não foi possível criar a conversa.");
      }
    },
  };
}

interface DocumentActionsProps {
  document: DocumentItem;
  onDeleted?: () => void;
  size?: "sm" | "md";
}

export function DocumentActions({ document, onDeleted, size = "sm" }: DocumentActionsProps) {
  const [dialog, setDialog] = useState<"rename" | "delete" | null>(null);
  const [title, setTitle] = useState(document.title);
  const rename = useRenameDocument();
  const reprocess = useReprocessDocument();
  const remove = useDeleteDocument();
  const chat = useStartChat();

  const canReprocess = document.status === "ready" || document.status === "failed";

  return (
    <div className="flex items-center gap-1">
      {document.status === "ready" && (
        <Button size={size} variant="secondary" onClick={() => chat.start(document)} loading={chat.pending}>
          {!chat.pending && <MessageSquarePlus />} Conversar
        </Button>
      )}
      <Button
        size="icon"
        variant="ghost"
        aria-label={`Renomear ${document.title}`}
        title="Renomear"
        onClick={() => {
          setTitle(document.title);
          setDialog("rename");
        }}
      >
        <Pencil />
      </Button>
      {canReprocess && (
        <Button
          size="icon"
          variant="ghost"
          aria-label={`Reprocessar ${document.title}`}
          title="Reprocessar"
          loading={reprocess.isPending}
          onClick={() =>
            reprocess.mutate(document.id, {
              onSuccess: () => toast.success("Reprocessamento iniciado."),
              onError: (error) => toast.error(error.message),
            })
          }
        >
          {!reprocess.isPending && <RotateCw />}
        </Button>
      )}
      <Button
        size="icon"
        variant="ghost"
        aria-label={`Excluir ${document.title}`}
        title="Excluir"
        className="hover:text-danger"
        onClick={() => setDialog("delete")}
      >
        <Trash2 />
      </Button>

      <Dialog
        open={dialog === "rename"}
        onClose={() => setDialog(null)}
        title="Renomear documento"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDialog(null)}>
              Cancelar
            </Button>
            <Button
              form={`rename-${document.id}`}
              type="submit"
              loading={rename.isPending}
              disabled={!title.trim() || title.trim() === document.title}
            >
              Salvar
            </Button>
          </>
        }
      >
        <form
          id={`rename-${document.id}`}
          onSubmit={(event) => {
            event.preventDefault();
            rename.mutate(
              { id: document.id, title: title.trim() },
              {
                onSuccess: () => {
                  toast.success("Documento renomeado.");
                  setDialog(null);
                },
                onError: (error) => toast.error(error.message),
              },
            );
          }}
        >
          <Field label="Título" htmlFor={`title-${document.id}`}>
            <Input
              id={`title-${document.id}`}
              value={title}
              maxLength={255}
              onChange={(event) => setTitle(event.target.value)}
              autoFocus
            />
          </Field>
        </form>
      </Dialog>

      <Dialog
        open={dialog === "delete"}
        onClose={() => setDialog(null)}
        title="Excluir documento?"
        description={`"${document.title}" será removido junto com seus trechos indexados e as citações nas conversas. Esta ação não pode ser desfeita.`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDialog(null)}>
              Cancelar
            </Button>
            <Button
              variant="danger"
              loading={remove.isPending}
              onClick={() =>
                remove.mutate(document.id, {
                  onSuccess: () => {
                    toast.success("Documento excluído.");
                    setDialog(null);
                    onDeleted?.();
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
