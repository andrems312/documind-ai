"use client";

import { CheckCircle2, FileUp, Loader2, XCircle } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { validateFile } from "@/components/documents/validate-file";
import { Progress } from "@/components/ui/progress";
import { useUploadDocument } from "@/hooks/use-documents";
import { MAX_UPLOAD_MB } from "@/lib/constants";
import { cn } from "@/lib/utils/cn";
import { formatBytes } from "@/lib/utils/format";

interface UploadItem {
  key: string;
  name: string;
  size: number;
  progress: number;
  state: "uploading" | "done" | "error";
  message?: string;
}

export function UploadDropzone({ compact = false }: { compact?: boolean }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [items, setItems] = useState<UploadItem[]>([]);
  const upload = useUploadDocument();

  const update = (key: string, patch: Partial<UploadItem>) =>
    setItems((list) => list.map((item) => (item.key === key ? { ...item, ...patch } : item)));

  async function handleFiles(files: FileList | File[]) {
    for (const file of Array.from(files)) {
      const key = `${file.name}-${file.size}-${Date.now()}`;
      const problem = validateFile(file);
      if (problem) {
        toast.error(`${file.name}: ${problem}`);
        continue;
      }
      setItems((list) => [{ key, name: file.name, size: file.size, progress: 0, state: "uploading" }, ...list]);
      try {
        await upload.mutateAsync({ file, onProgress: (progress) => update(key, { progress }) });
        update(key, { state: "done", progress: 1 });
        toast.success(`${file.name} enviado. O processamento começou.`);
        setTimeout(() => setItems((list) => list.filter((item) => item.key !== key)), 2500);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Falha no envio.";
        update(key, { state: "error", message });
        toast.error(`${file.name}: ${message}`);
      }
    }
  }

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          void handleFiles(event.dataTransfer.files);
        }}
        className={cn(
          "group flex w-full flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border-strong bg-surface text-center transition-colors",
          compact ? "px-4 py-6" : "px-6 py-10",
          dragging ? "border-accent bg-accent-soft" : "hover:border-accent/60 hover:bg-surface-2",
        )}
      >
        <span
          className={cn(
            "flex size-11 items-center justify-center rounded-xl bg-accent-soft transition-transform",
            dragging ? "scale-110" : "group-hover:scale-105",
          )}
        >
          <FileUp className="size-5 text-accent" aria-hidden />
        </span>
        <span className="text-sm font-medium">
          {dragging ? "Solte para enviar" : "Arraste PDFs aqui ou clique para escolher"}
        </span>
        <span className="text-xs text-fg-subtle">Somente PDF com texto, até {MAX_UPLOAD_MB} MB cada</span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        hidden
        onChange={(event) => {
          if (event.target.files) void handleFiles(event.target.files);
          event.target.value = "";
        }}
      />

      {items.length > 0 && (
        <ul className="space-y-2" aria-live="polite">
          {items.map((item) => (
            <li key={item.key} className="rounded-md border border-border bg-surface px-3 py-2.5 animate-fade-in">
              <div className="flex items-center gap-2 text-sm">
                {item.state === "uploading" && <Loader2 className="size-4 animate-spin text-accent" />}
                {item.state === "done" && <CheckCircle2 className="size-4 text-success" />}
                {item.state === "error" && <XCircle className="size-4 text-danger" />}
                <span className="min-w-0 flex-1 truncate font-medium">{item.name}</span>
                <span className="text-xs text-fg-subtle">{formatBytes(item.size)}</span>
              </div>
              {item.state === "uploading" && (
                <Progress value={item.progress} label={`Envio de ${item.name}`} className="mt-2" />
              )}
              {item.state === "error" && <p className="mt-1 text-xs text-danger">{item.message}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
