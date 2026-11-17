"use client";

import { Activity, FileText, Layers, MessageSquareText, Upload } from "lucide-react";
import Link from "next/link";
import { DocumentStatusBadge } from "@/components/documents/document-status";
import { EmptyState } from "@/components/layout/empty-state";
import { PageHeader } from "@/components/layout/page-header";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useConversations } from "@/hooks/use-conversations";
import { useDocuments } from "@/hooks/use-documents";
import { useApiHealth, useMe } from "@/hooks/use-me";
import { formatRelative, pluralize } from "@/lib/utils/format";

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Bom dia";
  if (hour < 18) return "Boa tarde";
  return "Boa noite";
}

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
  loading,
}: {
  icon: typeof FileText;
  label: string;
  value: string | number;
  hint: string;
  loading: boolean;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-fg-muted">
          <Icon className="size-4" /> {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-9 w-16" />
        ) : (
          <p className="text-3xl font-semibold tracking-tight">{value}</p>
        )}
        <CardDescription className="mt-1">{hint}</CardDescription>
      </CardContent>
    </Card>
  );
}

export function DashboardView() {
  const me = useMe();
  const health = useApiHealth();
  const documents = useDocuments();
  const conversations = useConversations();

  const docs = documents.data ?? [];
  const ready = docs.filter((d) => d.status === "ready");
  const processing = docs.filter((d) => d.status === "uploaded" || d.status === "processing");
  const pages = ready.reduce((sum, d) => sum + (d.page_count ?? 0), 0);

  return (
    <>
      <PageHeader
        title={
          me.isPending
            ? "Carregando…"
            : `${greeting()}, ${me.data?.full_name?.split(" ")[0] ?? "por aí"}`
        }
        description="Sua biblioteca de documentos e conversas em um só lugar."
        actions={
          <Button asChild>
            <Link href="/documents">
              <Upload /> Enviar PDF
            </Link>
          </Button>
        }
      />

      {me.isError && (
        <Alert tone="danger" title="Não foi possível carregar seu perfil" className="mb-6">
          {me.error.message} Verifique se a API está em execução e se as variáveis de ambiente estão
          corretas.
        </Alert>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={FileText}
          label="Documentos"
          value={docs.length}
          hint={processing.length ? `${processing.length} em processamento` : `${ready.length} prontos para consulta`}
          loading={documents.isPending}
        />
        <StatCard
          icon={Layers}
          label="Páginas indexadas"
          value={pages}
          hint="Disponíveis para busca e citação"
          loading={documents.isPending}
        />
        <StatCard
          icon={MessageSquareText}
          label="Conversas"
          value={conversations.data?.length ?? 0}
          hint="Histórico salvo com as fontes"
          loading={conversations.isPending}
        />
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-fg-muted">
              <Activity className="size-4" /> Status da API
            </CardTitle>
          </CardHeader>
          <CardContent>
            {health.isPending ? (
              <div className="space-y-2">
                <Skeleton className="h-6 w-24" />
                <Skeleton className="h-3 w-40" />
              </div>
            ) : health.isError ? (
              <>
                <Badge variant="danger">Indisponível</Badge>
                <CardDescription className="mt-2">{health.error.message}</CardDescription>
              </>
            ) : (
              <>
                <Badge variant={health.data.status === "ok" ? "success" : "warning"}>
                  {health.data.status === "ok" ? "Operacional" : "Degradado"}
                </Badge>
                <ul className="mt-2 space-y-0.5 text-xs text-fg-muted">
                  {Object.entries(health.data.checks).map(([name, value]) => (
                    <li key={name} className="flex justify-between gap-2">
                      <span className="font-mono">{name}</span>
                      <span>{value}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-fg-muted">Documentos recentes</h2>
          {docs.length > 0 && (
            <Link href="/documents" className="text-sm text-accent hover:underline">
              Ver todos
            </Link>
          )}
        </div>
        {documents.isPending ? (
          <div className="space-y-2">
            <Skeleton className="h-14" />
            <Skeleton className="h-14" />
          </div>
        ) : docs.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="Nenhum documento ainda"
            description="Envie seu primeiro PDF para começar a fazer perguntas com respostas fundamentadas e citação de página."
            action={
              <Button asChild variant="secondary">
                <Link href="/documents">Ir para Documentos</Link>
              </Button>
            }
          />
        ) : (
          <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-surface">
            {docs.slice(0, 5).map((document) => (
              <li key={document.id}>
                <Link
                  href={`/documents/${document.id}`}
                  className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-surface-2"
                >
                  <FileText className="size-4 shrink-0 text-fg-subtle" />
                  <span className="min-w-0 flex-1 truncate text-sm font-medium">{document.title}</span>
                  <span className="hidden text-xs text-fg-subtle sm:inline">
                    {document.page_count ? pluralize(document.page_count, "página", "páginas") : ""} ·{" "}
                    {formatRelative(document.created_at)}
                  </span>
                  <DocumentStatusBadge status={document.status} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
