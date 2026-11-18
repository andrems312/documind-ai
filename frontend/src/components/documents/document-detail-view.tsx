"use client";

import { ArrowLeft, ChevronLeft, ChevronRight, ExternalLink, FileText } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { AnalysisPanel } from "@/components/analyses/analysis-panel";
import { DocumentActions } from "@/components/documents/document-actions";
import { DocumentProgress, DocumentStatusBadge } from "@/components/documents/document-status";
import { EmptyState } from "@/components/layout/empty-state";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useDocument, useDocumentPage } from "@/hooks/use-documents";
import { apiBlob } from "@/lib/api/client";
import { formatBytes, formatRelative, pluralize } from "@/lib/utils/format";
import { findHighlight } from "@/lib/utils/highlight";

function PageText({ text, highlight }: { text: string; highlight: string | null }) {
  const markRef = useRef<HTMLElement>(null);
  const range = useMemo(() => (highlight ? findHighlight(text, highlight) : null), [text, highlight]);

  useEffect(() => {
    markRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [range]);

  if (!text.trim()) {
    return <p className="text-sm italic text-fg-subtle">Esta página não contém texto extraível.</p>;
  }
  if (!range) return <>{text}</>;
  return (
    <>
      {text.slice(0, range[0])}
      <mark ref={markRef} className="rounded-sm bg-cite-soft px-0.5 text-fg ring-1 ring-cite/40">
        {text.slice(range[0], range[1])}
      </mark>
      {text.slice(range[1])}
    </>
  );
}

export function DocumentDetailView() {
  const { id } = useParams<{ id: string }>();
  const params = useSearchParams();
  const router = useRouter();
  const document = useDocument(id);

  const initialPage = Math.max(1, Number(params.get("page")) || 1);
  const [page, setPage] = useState(initialPage);
  const [highlight, setHighlight] = useState<string | null>(params.get("hl"));
  const [jump, setJump] = useState(String(initialPage));
  const [opening, setOpening] = useState(false);

  const pageCount = document.data?.page_count ?? 0;
  const ready = document.data?.status === "ready";
  const pageQuery = useDocumentPage(id, page, ready);

  function goTo(target: number) {
    const next = Math.min(Math.max(1, target), Math.max(pageCount, 1));
    if (next !== page) setHighlight(null);
    setPage(next);
    setJump(String(next));
    router.replace(`/documents/${id}?page=${next}`, { scroll: false });
  }

  async function openOriginal() {
    // Abre a aba já no clique (antes do await) para não ser bloqueada como pop-up.
    const tab = window.open("", "_blank");
    setOpening(true);
    try {
      const blob = await apiBlob(`/api/v1/documents/${id}/file`);
      const url = URL.createObjectURL(blob);
      if (tab) tab.location.href = `${url}#page=${page}`;
      else window.location.href = url;
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (error) {
      tab?.close();
      toast.error(error instanceof Error ? error.message : "Não foi possível abrir o PDF.");
    } finally {
      setOpening(false);
    }
  }

  if (document.isPending) {
    return (
      <div className="space-y-4" aria-busy>
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-[420px] w-full" />
      </div>
    );
  }

  if (document.isError) {
    return (
      <EmptyState
        icon={FileText}
        title="Documento não encontrado"
        description={document.error.message}
        action={
          <Button asChild variant="secondary">
            <Link href="/documents">Voltar para Documentos</Link>
          </Button>
        }
      />
    );
  }

  const doc = document.data;
  return (
    <>
      <Link
        href="/documents"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-fg-muted hover:text-fg"
      >
        <ArrowLeft className="size-4" /> Documentos
      </Link>

      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="break-words text-2xl font-semibold tracking-tight">{doc.title}</h1>
            <DocumentStatusBadge status={doc.status} />
          </div>
          <p className="text-sm text-fg-muted">
            {doc.original_filename} · {doc.page_count ? pluralize(doc.page_count, "página", "páginas") : "—"} ·{" "}
            {formatBytes(doc.file_size)} · enviado {formatRelative(doc.created_at)}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={openOriginal} loading={opening}>
            {!opening && <ExternalLink />} Abrir PDF
          </Button>
          <DocumentActions document={doc} onDeleted={() => router.push("/documents")} />
        </div>
      </div>

      {doc.status === "failed" && (
        <Alert tone="danger" title="O processamento falhou" className="mb-6">
          {doc.error_message ?? "Erro desconhecido."} Você pode tentar reprocessar o documento.
        </Alert>
      )}
      {!ready && doc.status !== "failed" && (
        <Card className="mb-6 p-5">
          <DocumentProgress document={doc} />
        </Card>
      )}

      {ready && (
        <div className="mb-6">
          <AnalysisPanel documentId={id} />
        </div>
      )}

      {ready && (
        <Card className="overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-surface-2/50 px-4 py-2.5">
            <span className="text-sm font-medium">Texto extraído</span>
            <form
              className="flex items-center gap-1"
              onSubmit={(event) => {
                event.preventDefault();
                goTo(Number(jump) || 1);
              }}
            >
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="Página anterior"
                disabled={page <= 1}
                onClick={() => goTo(page - 1)}
              >
                <ChevronLeft />
              </Button>
              <label className="flex items-center gap-1.5 text-sm text-fg-muted">
                <span className="sr-only">Ir para a página</span>
                <Input
                  value={jump}
                  onChange={(event) => setJump(event.target.value.replace(/\D/g, ""))}
                  inputMode="numeric"
                  className="h-8 w-14 text-center font-mono"
                />
                <span className="font-mono">/ {pageCount}</span>
              </label>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="Próxima página"
                disabled={page >= pageCount}
                onClick={() => goTo(page + 1)}
              >
                <ChevronRight />
              </Button>
            </form>
          </div>
          <div className="max-h-[65vh] overflow-y-auto scrollbar-thin p-5 sm:p-8">
            {pageQuery.isPending ? (
              <div className="space-y-2" aria-busy>
                {Array.from({ length: 8 }).map((_, i) => (
                  <Skeleton key={i} className="h-3.5" style={{ width: `${70 + ((i * 13) % 30)}%` }} />
                ))}
              </div>
            ) : pageQuery.isError ? (
              <Alert tone="danger">{pageQuery.error.message}</Alert>
            ) : (
              <article className="whitespace-pre-wrap text-[15px] leading-7 text-fg">
                <PageText text={pageQuery.data.text} highlight={highlight} />
              </article>
            )}
          </div>
        </Card>
      )}
    </>
  );
}
