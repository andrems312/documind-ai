"use client";

import { Sparkles } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { AnalysisResult } from "@/components/analyses/analysis-result";
import { ANALYSIS_META } from "@/components/analyses/analysis-meta";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAnalyses,
  useAnalysis,
  useDeleteAnalysis,
  useGenerateAnalysis,
} from "@/hooks/use-analyses";
import { formatDate } from "@/lib/utils/format";
import type { AnalysisType } from "@/types/api";

/** Gera e lista análises (resumo, informações-chave) de um documento já processado. */
export function AnalysisPanel({ documentId }: { documentId: string }) {
  const analyses = useAnalyses();
  const generate = useGenerateAnalysis();
  const remove = useDeleteAnalysis();
  const [selected, setSelected] = useState<string | null>(null);
  const detail = useAnalysis(selected ?? "", !!selected);

  const forDoc = (analyses.data ?? []).filter((a) => a.document_ids.includes(documentId));

  function run(type: AnalysisType) {
    generate.mutate(
      { type, documentIds: [documentId] },
      {
        onSuccess: (analysis) => setSelected(analysis.id),
        onError: (error) => toast.error(error.message),
      },
    );
  }

  const pendingType = generate.isPending ? generate.variables?.type : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-fg-muted">
          <Sparkles className="size-4" /> Análises com IA
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {(["summary", "key_info"] as const).map((type) => {
            const meta = ANALYSIS_META[type];
            return (
              <Button
                key={type}
                variant="secondary"
                size="sm"
                onClick={() => run(type)}
                loading={pendingType === type}
                disabled={generate.isPending}
              >
                {pendingType !== type && <meta.icon />} {meta.verb}
              </Button>
            );
          })}
        </div>

        {generate.isPending && (
          <div className="space-y-2" aria-busy>
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-24 w-full" />
          </div>
        )}

        {!generate.isPending && selected && detail.data && (
          <AnalysisResult
            analysis={detail.data}
            deleting={remove.isPending}
            onDelete={(id) =>
              remove.mutate(id, {
                onSuccess: () => {
                  toast.success("Análise excluída.");
                  setSelected(null);
                },
                onError: (error) => toast.error(error.message),
              })
            }
          />
        )}

        {forDoc.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-medium text-fg-subtle">Análises salvas</p>
            <ul className="space-y-1.5">
              {forDoc.map((a) => {
                const meta = ANALYSIS_META[a.type];
                const active = a.id === selected;
                return (
                  <li key={a.id}>
                    <button
                      type="button"
                      onClick={() => setSelected(a.id)}
                      className={`flex w-full items-center gap-2 rounded-md border px-3 py-2 text-left text-sm transition-colors ${
                        active
                          ? "border-accent bg-accent-soft/50"
                          : "border-border hover:bg-surface-2"
                      }`}
                    >
                      <meta.icon className="size-4 shrink-0 text-fg-subtle" />
                      <span className="min-w-0 flex-1 truncate">{a.title}</span>
                      <span className="shrink-0 text-xs text-fg-subtle">{formatDate(a.created_at)}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
