import { AlertTriangle, CheckCircle2, Clock, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { DocumentItem } from "@/types/api";

const labels = {
  uploaded: { text: "Na fila", variant: "neutral", Icon: Clock },
  processing: { text: "Processando", variant: "accent", Icon: Loader2 },
  ready: { text: "Pronto", variant: "success", Icon: CheckCircle2 },
  failed: { text: "Falhou", variant: "danger", Icon: AlertTriangle },
} as const;

export function DocumentStatusBadge({ status }: { status: DocumentItem["status"] }) {
  const { text, variant, Icon } = labels[status];
  return (
    <Badge variant={variant}>
      <Icon className={status === "processing" ? "size-3 animate-spin" : "size-3"} aria-hidden />
      {text}
    </Badge>
  );
}

/** Barra de progresso para documentos ainda não prontos. */
export function DocumentProgress({ document }: { document: DocumentItem }) {
  if (document.status !== "uploaded" && document.status !== "processing") return null;
  const pages = document.page_count ?? 0;
  return (
    <div className="space-y-1">
      <Progress
        value={document.status === "uploaded" ? undefined : document.progress}
        label={`Processamento de ${document.title}`}
      />
      <p className="text-xs text-fg-subtle">
        {document.status === "uploaded"
          ? "Aguardando processamento…"
          : `Indexando: ${document.processed_pages} de ${pages} páginas`}
      </p>
    </div>
  );
}
