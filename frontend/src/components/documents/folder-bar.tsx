"use client";

import { FolderPlus, Layers, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  useCreateFolder,
  useDeleteFolder,
  useFolders,
  useUpdateFolder,
} from "@/hooks/use-folders";
import { cn } from "@/lib/utils/cn";
import type { Folder } from "@/types/api";

const DEFAULT_COLOR = "#7C6CF6";
const COLORS = [DEFAULT_COLOR, "#34D5C8", "#F59E0B", "#EF4444", "#22C55E", "#EC4899"];

function FolderDialog({
  open,
  onClose,
  folder,
}: {
  open: boolean;
  onClose: () => void;
  folder?: Folder;
}) {
  const create = useCreateFolder();
  const update = useUpdateFolder();
  const [name, setName] = useState(folder?.name ?? "");
  const [color, setColor] = useState(folder?.color ?? DEFAULT_COLOR);
  const editing = !!folder;
  const pending = create.isPending || update.isPending;

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const handlers = {
      onSuccess: () => {
        toast.success(editing ? "Pasta atualizada." : "Pasta criada.");
        onClose();
      },
      onError: (error: Error) => toast.error(error.message),
    };
    if (editing) update.mutate({ id: folder.id, name: name.trim(), color }, handlers);
    else create.mutate({ name: name.trim(), color }, handlers);
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={editing ? "Editar pasta" : "Nova pasta"}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button form="folder-form" type="submit" loading={pending} disabled={!name.trim()}>
            {editing ? "Salvar" : "Criar"}
          </Button>
        </>
      }
    >
      <form id="folder-form" onSubmit={submit} className="space-y-4">
        <Field label="Nome" htmlFor="folder-name">
          <Input
            id="folder-name"
            value={name}
            maxLength={80}
            onChange={(event) => setName(event.target.value)}
            placeholder="Ex.: Contratos"
            autoFocus
          />
        </Field>
        <div>
          <span className="mb-1.5 block text-sm font-medium text-fg-muted">Cor</span>
          <div className="flex gap-2">
            {COLORS.map((c) => (
              <button
                key={c}
                type="button"
                aria-label={`Cor ${c}`}
                onClick={() => setColor(c)}
                style={{ backgroundColor: c }}
                className={cn(
                  "size-7 rounded-full ring-offset-2 ring-offset-surface transition-all",
                  color.toLowerCase() === c.toLowerCase() ? "ring-2 ring-fg" : "hover:scale-110",
                )}
              />
            ))}
          </div>
        </div>
      </form>
    </Dialog>
  );
}

function Chip({
  active,
  onClick,
  color,
  children,
}: {
  active: boolean;
  onClick: () => void;
  color?: string | null;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition-colors",
        active ? "border-accent bg-accent-soft text-accent" : "border-border text-fg-muted hover:bg-surface-2",
      )}
    >
      {color && <span className="size-2 rounded-full" style={{ backgroundColor: color }} />}
      {children}
    </button>
  );
}

export function FolderBar({
  active,
  onChange,
}: {
  active: string | null;
  onChange: (id: string | null) => void;
}) {
  const folders = useFolders();
  const remove = useDeleteFolder();
  const [dialog, setDialog] = useState<{ mode: "create" } | { mode: "edit"; folder: Folder } | null>(
    null,
  );
  const [confirmDelete, setConfirmDelete] = useState<Folder | null>(null);

  const list = folders.data ?? [];
  const activeFolder = list.find((f) => f.id === active) ?? null;

  return (
    <div className="mb-5 space-y-2">
      <div className="flex items-center gap-2 overflow-x-auto scrollbar-thin pb-1">
        <Chip active={active === null} onClick={() => onChange(null)}>
          <Layers className="size-3.5" /> Todos
        </Chip>
        {list.map((folder) => (
          <Chip
            key={folder.id}
            active={active === folder.id}
            onClick={() => onChange(folder.id)}
            color={folder.color}
          >
            {folder.name}
            <span className="text-xs text-fg-subtle">{folder.document_count}</span>
          </Chip>
        ))}
        <Button
          variant="ghost"
          size="sm"
          className="shrink-0"
          onClick={() => setDialog({ mode: "create" })}
        >
          <FolderPlus /> Nova pasta
        </Button>
      </div>

      {activeFolder && (
        <div className="flex items-center gap-1 text-xs text-fg-subtle">
          <span>Pasta “{activeFolder.name}”</span>
          <Button
            size="icon"
            variant="ghost"
            className="size-6"
            aria-label="Editar pasta"
            onClick={() => setDialog({ mode: "edit", folder: activeFolder })}
          >
            <Pencil className="size-3.5" />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="size-6 hover:text-danger"
            aria-label="Excluir pasta"
            onClick={() => setConfirmDelete(activeFolder)}
          >
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      )}

      {dialog && (
        <FolderDialog
          open
          onClose={() => setDialog(null)}
          folder={dialog.mode === "edit" ? dialog.folder : undefined}
        />
      )}

      <Dialog
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        title="Excluir pasta?"
        description={`A pasta "${confirmDelete?.name}" será removida. Os documentos dela não são apagados — apenas ficam sem pasta.`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmDelete(null)}>
              Cancelar
            </Button>
            <Button
              variant="danger"
              loading={remove.isPending}
              onClick={() =>
                confirmDelete &&
                remove.mutate(confirmDelete.id, {
                  onSuccess: () => {
                    toast.success("Pasta excluída.");
                    if (active === confirmDelete.id) onChange(null);
                    setConfirmDelete(null);
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
