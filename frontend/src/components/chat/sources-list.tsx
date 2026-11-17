import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils/cn";
import type { Citation } from "@/types/api";

export function sourceHref(citation: Citation): string {
  const hl = encodeURIComponent(citation.excerpt.slice(0, 220));
  return `/documents/${citation.document_id}?page=${citation.page_number}&hl=${hl}`;
}

interface SourcesListProps {
  messageId: string;
  citations: Citation[];
  activeRank: number | null;
}

/** Fontes de uma resposta: documento, página e o trecho exato enviado ao modelo. */
export function SourcesList({ messageId, citations, activeRank }: SourcesListProps) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-4">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-fg-subtle">Fontes</p>
      <ol className="grid gap-2 sm:grid-cols-2">
        {citations.map((citation) => (
          <li
            key={citation.id}
            id={`source-${messageId}-${citation.rank}`}
            className={cn(
              "group rounded-md border bg-surface p-3 transition-[border-color,box-shadow] duration-300",
              activeRank === citation.rank ? "border-cite ring-2 ring-cite/25" : "border-border",
            )}
          >
            <Link href={sourceHref(citation)} className="block space-y-1.5">
              <span className="flex items-center gap-2 text-xs">
                <span className="flex h-[18px] min-w-[18px] items-center justify-center rounded-[5px] bg-cite-soft px-1 font-mono font-semibold text-cite">
                  {citation.rank}
                </span>
                <span className="min-w-0 flex-1 truncate font-medium text-fg">{citation.document_title}</span>
                <span className="shrink-0 font-mono text-fg-subtle">p. {citation.page_number}</span>
                <ArrowUpRight className="size-3.5 shrink-0 text-fg-subtle transition-colors group-hover:text-cite" />
              </span>
              <span className="line-clamp-3 block text-xs leading-relaxed text-fg-muted">
                {citation.excerpt}
              </span>
            </Link>
          </li>
        ))}
      </ol>
    </div>
  );
}
