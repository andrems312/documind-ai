"use client";

import { Activity, FileText, MessageSquareText, Upload } from "lucide-react";
import Link from "next/link";
import { EmptyState } from "@/components/layout/empty-state";
import { PageHeader } from "@/components/layout/page-header";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApiHealth, useMe } from "@/hooks/use-me";

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Bom dia";
  if (hour < 18) return "Boa tarde";
  return "Boa noite";
}

export function DashboardView() {
  const me = useMe();
  const health = useApiHealth();

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
          {me.error.message} Verifique se a API está em execução e se as variáveis de ambiente estão corretas.
        </Alert>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-fg-muted">
              <FileText className="size-4" /> Documentos
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold tracking-tight">0</p>
            <CardDescription>Disponível após a FASE 3 (upload e processamento).</CardDescription>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-fg-muted">
              <MessageSquareText className="size-4" /> Conversas
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold tracking-tight">0</p>
            <CardDescription>Disponível após a FASE 3 (chat com citações).</CardDescription>
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
                <Skeleton className="h-7 w-24" />
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
        <EmptyState
          icon={FileText}
          title="Nenhum documento ainda"
          description="Envie seu primeiro PDF para começar a fazer perguntas, gerar resumos e comparar conteúdos."
          action={
            <Button asChild variant="secondary">
              <Link href="/documents">Ir para Documentos</Link>
            </Button>
          }
        />
      </section>
    </>
  );
}
