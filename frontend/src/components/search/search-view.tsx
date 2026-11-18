"use client";

import { FileText, Loader2, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { EmptyState } from "@/components/layout/empty-state";
import { PageHeader } from "@/components/layout/page-header";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useFolders } from "@/hooks/use-folders";
import { useSearch } from "@/hooks/use-search";
import { pluralize } from "@/lib/utils/format";
import type { SearchResultItem } from "@/types/api";

function Highlighted({ text, query }: { text: string; query: string }) {
  const terms = useMemo(
    () => query.trim().split(/\s+/).filter((t) => t.length >= 3),
    [query],
  );
  if (terms.length === 0) return <>{text}</>;
  const pattern = new RegExp(`(${terms.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "gi");
  return (
    <>
      {text.split(pattern).map((part, i) =>
        pattern.test(part) ? (
          <mark key={i} className="rounded-sm bg-cite-soft px-0.5 text-fg">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}

function ResultCard({ item, query }: { item: SearchResultItem; query: string }) {
  return (
    <li>
      <Link
        href={`/documents/${item.document_id}?page=${item.page_number}&hl=${encodeURIComponent(query)}`}
        className="block rounded-lg border border-border bg-surface p-4 transition-colors hover:border-border-strong"
      >
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <FileText className="size-4 shrink-0 text-accent" />
          <span className="min-w-0 flex-1 truncate text-sm font-medium">{item.document_title}</span>
          <Badge variant="neutral">pág. {item.page_number}</Badge>
          <Badge variant="cite">{Math.round(item.similarity * 100)}% afinidade</Badge>
        </div>
        <p className="line-clamp-3 text-sm leading-6 text-fg-muted">
          <Highlighted text={item.excerpt} query={query} />
        </p>
      </Link>
    </li>
  );
}

export function SearchView() {
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [folderId, setFolderId] = useState<string>("");
  const folders = useFolders();
  const search = useSearch(query, folderId || null);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setQuery(input.trim());
  }

  const results = search.data?.results ?? [];

  return (
    <>
      <PageHeader
        title="Busca semântica"
        description="Encontre trechos por significado em toda a sua biblioteca, não só por palavra exata."
      />

      <form onSubmit={submit} className="mb-6 flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-fg-subtle" />
          <Input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ex.: multa por rescisão antecipada"
            aria-label="Termo de busca"
            className="pl-9"
          />
        </div>
        {(folders.data?.length ?? 0) > 0 && (
          <select
            value={folderId}
            onChange={(event) => setFolderId(event.target.value)}
            aria-label="Filtrar por pasta"
            className="h-10 rounded-md border border-border bg-surface px-3 text-sm text-fg outline-none focus-visible:ring-2 focus-visible:ring-accent/50 sm:w-52"
          >
            <option value="">Todas as pastas</option>
            {folders.data?.map((folder) => (
              <option key={folder.id} value={folder.id}>
                {folder.name}
              </option>
            ))}
          </select>
        )}
        <Button type="submit" disabled={input.trim().length < 2}>
          Buscar
        </Button>
      </form>

      {!query ? (
        <EmptyState
          icon={Search}
          title="Busque por significado"
          description="Digite uma pergunta ou tema. A busca entende o sentido, então sinônimos e paráfrases também encontram o trecho certo."
        />
      ) : search.isFetching ? (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-fg-muted">
          <Loader2 className="size-4 animate-spin" /> Buscando “{query}”…
        </div>
      ) : search.isError ? (
        <Alert tone="danger" title="A busca falhou">
          {search.error.message}
        </Alert>
      ) : results.length === 0 ? (
        <EmptyState
          icon={Search}
          title="Nenhum trecho encontrado"
          description={`Não encontramos nada relevante para “${query}”. Tente outras palavras ou verifique se há documentos processados.`}
        />
      ) : (
        <>
          <p className="mb-3 text-sm text-fg-muted">
            {pluralize(results.length, "trecho encontrado", "trechos encontrados")} para “{query}”
          </p>
          <ul className="space-y-3">
            {results.map((item) => (
              <ResultCard key={item.chunk_id} item={item} query={query} />
            ))}
          </ul>
        </>
      )}
    </>
  );
}
