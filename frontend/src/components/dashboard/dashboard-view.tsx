"use client";

import { Activity, FileText, Layers, MessageSquareText, Sparkles, Upload, Zap } from "lucide-react";
import Link from "next/link";
import { DocumentStatusBadge } from "@/components/documents/document-status";
import { UsageChart } from "@/components/dashboard/usage-chart";
import { EmptyState } from "@/components/layout/empty-state";
import { PageHeader } from "@/components/layout/page-header";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useDocuments } from "@/hooks/use-documents";
import { useApiHealth, useMe } from "@/hooks/use-me";
import { useStats } from "@/hooks/use-stats";
import { formatCompact, formatNumber, formatRelative, pluralize } from "@/lib/utils/format";

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
  const stats = useStats();
  const documents = useDocuments();

  const s = stats.data;
  const docs = documents.data ?? [];
  const tokens = s ? s.prompt_tokens + s.completion_tokens : 0;
  const processing = s?.documents.processing ?? 0;
  const ready = s?.documents.ready ?? 0;

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
          value={s?.documents.total ?? 0}
          hint={
            processing
              ? `${pluralize(processing, "em processamento", "em processamento")}`
              : `${pluralize(ready, "pronto", "prontos")} para consulta`
          }
          loading={stats.isPending}
        />
        <StatCard
          icon={Layers}
          label="Páginas indexadas"
          value={formatNumber(s?.pages_indexed ?? 0)}
          hint={`${formatNumber(s?.chunks ?? 0)} trechos para busca e citação`}
          loading={stats.isPending}
        />
        <StatCard
          icon={MessageSquareText}
          label="Conversas"
          value={s?.conversations ?? 0}
          hint={`${pluralize(s?.questions ?? 0, "pergunta", "perguntas")} respondidas`}
          loading={stats.isPending}
        />
        <StatCard
          icon={Zap}
          label="Tokens usados"
          value={formatCompact(tokens)}
          hint={`${pluralize(s?.analyses ?? 0, "análise", "análises")} geradas`}
          loading={stats.isPending}
        />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-fg-muted">
              <Activity className="size-4" /> Consumo recente
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats.isPending ? (
              <Skeleton className="h-40 w-full" />
            ) : s ? (
              <UsageChart data={s.daily_usage} />
            ) : (
              <p className="text-sm text-fg-muted">Sem dados de uso ainda.</p>
            )}
          </CardContent>
        </Card>
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
        <p className="mt-6 flex items-center gap-2 text-xs text-fg-subtle">
          <Sparkles className="size-3.5" /> Dica: gere resumos e extraia informações-chave a partir de
          qualquer documento pronto.
        </p>
      </section>
    </>
  );
}
