"use client";

import { FileText, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { DocumentActions } from "@/components/documents/document-actions";
import { DocumentProgress, DocumentStatusBadge } from "@/components/documents/document-status";
import { FolderBar } from "@/components/documents/folder-bar";
import { UploadDropzone } from "@/components/documents/upload-dropzone";
import { EmptyState } from "@/components/layout/empty-state";
import { PageHeader } from "@/components/layout/page-header";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useDocuments } from "@/hooks/use-documents";
import { useFolders } from "@/hooks/use-folders";
import { formatBytes, formatRelative, pluralize } from "@/lib/utils/format";
import type { DocumentItem } from "@/types/api";

function DocumentRow({ document, folderName }: { document: DocumentItem; folderName?: string }) {
  return (
    <li className="flex flex-col gap-3 rounded-lg border border-border bg-surface p-4 shadow-card transition-colors hover:border-border-strong sm:flex-row sm:items-center animate-fade-in">
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-accent-soft">
          <FileText className="size-5 text-accent" aria-hidden />
        </div>
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href={`/documents/${document.id}`}
              className="truncate font-medium hover:text-accent hover:underline underline-offset-4"
            >
              {document.title}
            </Link>
            <DocumentStatusBadge status={document.status} />
            {folderName && <Badge variant="neutral">{folderName}</Badge>}
          </div>
          <p className="text-xs text-fg-subtle">
            {document.page_count ? pluralize(document.page_count, "página", "páginas") : "—"} ·{" "}
            {formatBytes(document.file_size)} · enviado {formatRelative(document.created_at)}
          </p>
          <DocumentProgress document={document} />
          {document.status === "failed" && document.error_message && (
            <p className="text-xs text-danger">{document.error_message}</p>
          )}
        </div>
      </div>
      <DocumentActions document={document} />
    </li>
  );
}

function ListSkeleton() {
  return (
    <ul className="space-y-3" aria-busy aria-label="Carregando documentos">
      {Array.from({ length: 3 }).map((_, i) => (
        <li key={i} className="flex items-center gap-3 rounded-lg border border-border bg-surface p-4">
          <Skeleton className="size-10" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <Skeleton className="h-8 w-24" />
        </li>
      ))}
    </ul>
  );
}

export function DocumentsView() {
  const documents = useDocuments();
  const folders = useFolders();
  const [query, setQuery] = useState("");
  const [folder, setFolder] = useState<string | null>(null);

  const folderName = useMemo(() => {
    const map = new Map((folders.data ?? []).map((f) => [f.id, f.name]));
    return (id: string | null) => (id ? map.get(id) : undefined);
  }, [folders.data]);

  const filtered = useMemo(() => {
    const term = query.trim().toLocaleLowerCase("pt-BR");
    let list = documents.data ?? [];
    if (folder !== null) list = list.filter((d) => d.folder_id === folder);
    return term ? list.filter((d) => d.title.toLocaleLowerCase("pt-BR").includes(term)) : list;
  }, [documents.data, query, folder]);

  const total = documents.data?.length ?? 0;

  return (
    <>
      <PageHeader
        title="Documentos"
        description="Envie PDFs. Cada arquivo é dividido em trechos, indexado e fica pronto para perguntas."
      />

      <section className="mb-8">
        <UploadDropzone compact={total > 0} />
      </section>

      <section aria-labelledby="library-heading">
        {total > 0 && <FolderBar active={folder} onChange={setFolder} />}
        <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 id="library-heading" className="text-sm font-semibold text-fg-muted">
            Biblioteca {total > 0 && <span className="font-normal">({filtered.length})</span>}
          </h2>
          {total > 0 && (
            <div className="relative sm:w-72">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-fg-subtle" />
              <Input
                aria-label="Filtrar documentos por título"
                placeholder="Filtrar por título…"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="pl-9"
              />
            </div>
          )}
        </div>

        {documents.isPending ? (
          <ListSkeleton />
        ) : documents.isError ? (
          <Alert tone="danger" title="Não foi possível carregar os documentos">
            {documents.error.message}
          </Alert>
        ) : total === 0 ? (
          <EmptyState
            icon={FileText}
            title="Sua biblioteca está vazia"
            description="Envie o primeiro PDF acima. Assim que ele for processado, você poderá conversar com o conteúdo."
          />
        ) : filtered.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border-strong p-6 text-center text-sm text-fg-muted">
            Nenhum documento corresponde a “{query}”.
          </p>
        ) : (
          <ul className="space-y-3">
            {filtered.map((document) => (
              <DocumentRow
                key={document.id}
                document={document}
                folderName={folderName(document.folder_id)}
              />
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
