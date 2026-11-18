"use client";

import { Download, FileType, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { AnswerContent } from "@/components/chat/answer-content";
import { ANALYSIS_META } from "@/components/analyses/analysis-meta";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { downloadFromApi } from "@/lib/utils/download";
import { formatDate } from "@/lib/utils/format";
import type { Analysis } from "@/types/api";

function slug(text: string): string {
  return (
    text
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60) || "analise"
  );
}

interface AnalysisResultProps {
  analysis: Analysis;
  onDelete?: (id: string) => void;
  deleting?: boolean;
}

export function AnalysisResult({ analysis, onDelete, deleting }: AnalysisResultProps) {
  const meta = ANALYSIS_META[analysis.type];
  const [exporting, setExporting] = useState<"md" | "pdf" | null>(null);

  async function exportAs(format: "md" | "pdf") {
    setExporting(format);
    try {
      await downloadFromApi(
        `/api/v1/analyses/${analysis.id}/export?format=${format}`,
        `${slug(analysis.title)}.${format}`,
      );
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Não foi possível exportar.");
    } finally {
      setExporting(null);
    }
  }

  return (
    <Card className="animate-fade-in overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border bg-surface-2/40 px-5 py-3">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant="accent">
              <meta.icon className="size-3" /> {meta.label}
            </Badge>
            <span className="text-xs text-fg-subtle">{formatDate(analysis.created_at)}</span>
          </div>
          <h3 className="truncate text-sm font-semibold">{analysis.title}</h3>
        </div>
        <div className="flex items-center gap-1">
          <Button size="sm" variant="outline" onClick={() => exportAs("md")} loading={exporting === "md"}>
            {exporting !== "md" && <Download />} .md
          </Button>
          <Button size="sm" variant="outline" onClick={() => exportAs("pdf")} loading={exporting === "pdf"}>
            {exporting !== "pdf" && <FileType />} .pdf
          </Button>
          {onDelete && (
            <Button
              size="icon"
              variant="ghost"
              className="hover:text-danger"
              aria-label="Excluir análise"
              title="Excluir análise"
              loading={deleting}
              onClick={() => onDelete(analysis.id)}
            >
              {!deleting && <Trash2 />}
            </Button>
          )}
        </div>
      </div>
      <div className="max-h-[60vh] overflow-y-auto scrollbar-thin px-5 py-4">
        <AnswerContent content={analysis.content} />
      </div>
    </Card>
  );
}
