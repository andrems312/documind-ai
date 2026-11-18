"use client";

import { FileText, Scale } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { AnalysisResult } from "@/components/analyses/analysis-result";
import { EmptyState } from "@/components/layout/empty-state";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAnalyses,
  useAnalysis,
  useDeleteAnalysis,
  useGenerateAnalysis,
} from "@/hooks/use-analyses";
import { useDocuments } from "@/hooks/use-documents";
import { cn } from "@/lib/utils/cn";
import { formatDate, pluralize } from "@/lib/utils/format";

export function CompareView() {
  const documents = useDocuments();
  const analyses = useAnalyses();
  const generate = useGenerateAnalysis();
  const remove = useDeleteAnalysis();
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set());
  const [shownId, setShownId] = useState<string | null>(null);
  const detail = useAnalysis(shownId ?? "", !!shownId);

  const ready = (documents.data ?? []).filter((d) => d.status === "ready");
  const comparisons = (analyses.data ?? []).filter((a) => a.type === "comparison");

  function toggle(id: string) {
    setSelectedDocs((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function compare() {
    generate.mutate(
      { type: "comparison", documentIds: [...selectedDocs] },
      {
        onSuccess: (analysis) => {
          setShownId(analysis.id);
          toast.success("Comparação gerada.");
        },
        onError: (error) => toast.error(error.message),
      },
    );
  }

  if (!documents.isPending && ready.length < 2) {
    return (
      <>
        <PageHeader
          title="Comparar documentos"
          description="Identifique semelhanças e diferenças entre dois ou mais documentos."
        />
        <EmptyState
          icon={Scale}
          title="Você precisa de pelo menos dois documentos prontos"
          description="Envie e processe mais documentos para poder compará-los."
          action={
            <Button asChild variant="secondary">
              <Link href="/documents">Ir para Documentos</Link>
            </Button>
          }
        />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Comparar documentos"
        description="Selecione os documentos e deixe a IA apontar semelhanças e diferenças, com base apenas no conteúdo."
      />

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-fg-muted">
              Documentos ({selectedDocs.size} selecionados)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {documents.isPending ? (
              <div className="space-y-2">
                <Skeleton className="h-11" />
                <Skeleton className="h-11" />
              </div>
            ) : (
              <ul className="max-h-[50vh] space-y-1.5 overflow-y-auto scrollbar-thin pr-1">
                {ready.map((document) => {
                  const checked = selectedDocs.has(document.id);
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
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}
            <Button
              className="w-full"
              onClick={compare}
              loading={generate.isPending}
              disabled={selectedDocs.size < 2 || generate.isPending}
            >
              {!generate.isPending && <Scale />}
              {selectedDocs.size < 2
                ? "Selecione 2 ou mais"
                : `Comparar ${pluralize(selectedDocs.size, "documento", "documentos")}`}
            </Button>
          </CardContent>
        </Card>

        <div className="space-y-4">
          {generate.isPending && (
            <Card>
              <CardContent className="space-y-3">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-40 w-full" />
              </CardContent>
            </Card>
          )}

          {!generate.isPending && shownId && detail.data && (
            <AnalysisResult
              analysis={detail.data}
              deleting={remove.isPending}
              onDelete={(id) =>
                remove.mutate(id, {
                  onSuccess: () => {
                    toast.success("Comparação excluída.");
                    setShownId(null);
                  },
                  onError: (error) => toast.error(error.message),
                })
              }
            />
          )}

          {!generate.isPending && !shownId && (
            <EmptyState
              icon={Scale}
              title="Nenhuma comparação aberta"
              description="Selecione documentos à esquerda e clique em Comparar, ou abra uma comparação salva abaixo."
            />
          )}

          {comparisons.length > 0 && (
            <div>
              <p className="mb-2 text-xs font-medium text-fg-subtle">Comparações salvas</p>
              <ul className="space-y-1.5">
                {comparisons.map((a) => (
                  <li key={a.id}>
                    <button
                      type="button"
                      onClick={() => setShownId(a.id)}
                      className={cn(
                        "flex w-full items-center gap-2 rounded-md border px-3 py-2 text-left text-sm transition-colors",
                        a.id === shownId ? "border-accent bg-accent-soft/50" : "border-border hover:bg-surface-2",
                      )}
                    >
                      <Scale className="size-4 shrink-0 text-fg-subtle" />
                      <span className="min-w-0 flex-1 truncate">{a.title}</span>
                      <span className="shrink-0 text-xs text-fg-subtle">{formatDate(a.created_at)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
