import { ArrowRight, FileSearch, Quote, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { ThemeToggle } from "@/components/layout/theme-toggle";

const highlights = [
  {
    icon: FileSearch,
    title: "RAG de verdade",
    text: "Cada resposta nasce dos trechos recuperados dos seus PDFs, nunca da imaginação do modelo.",
  },
  {
    icon: Quote,
    title: "Fontes com página",
    text: "Veja exatamente de qual página e parágrafo a informação foi retirada.",
  },
  {
    icon: ShieldCheck,
    title: "Seus dados, isolados",
    text: "Autenticação Supabase, políticas por usuário no banco e arquivos privados.",
  },
];

export default function LandingPage() {
  return (
    <main className="relative min-h-dvh overflow-hidden bg-grid">
      <div
        className="pointer-events-none absolute -top-40 left-1/2 h-[480px] w-[720px] -translate-x-1/2 rounded-full bg-accent/25 blur-[120px]"
        aria-hidden
      />
      <header className="relative mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Logo />
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button asChild variant="ghost" size="sm">
            <Link href="/login">Entrar</Link>
          </Button>
          <Button asChild size="sm">
            <Link href="/register">Criar conta</Link>
          </Button>
        </div>
      </header>

      <section className="relative mx-auto max-w-4xl px-6 pb-24 pt-20 text-center animate-rise">
        <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-fg-muted">
          <span className="size-1.5 rounded-full bg-cite" /> Respostas fundamentadas em documentos
        </span>
        <h1 className="mt-6 text-balance text-4xl font-semibold tracking-tight sm:text-6xl">
          Converse com seus documentos.
          <span className="block text-accent">Com as fontes na mão.</span>
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-pretty text-base text-fg-muted sm:text-lg">
          Envie PDFs, pergunte em português e receba respostas que citam a página de origem. Resuma,
          compare e busque semanticamente em toda a sua biblioteca.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/register">
              Começar agora <ArrowRight />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/login">Já tenho conta</Link>
          </Button>
        </div>
      </section>

      <section className="relative mx-auto grid max-w-5xl gap-4 px-6 pb-24 sm:grid-cols-3">
        {highlights.map(({ icon: Icon, title, text }) => (
          <div
            key={title}
            className="rounded-lg border border-border bg-surface/80 p-5 shadow-card backdrop-blur"
          >
            <div className="mb-3 flex size-9 items-center justify-center rounded-md bg-accent-soft">
              <Icon className="size-4 text-accent" aria-hidden />
            </div>
            <h2 className="font-semibold">{title}</h2>
            <p className="mt-1 text-sm text-fg-muted">{text}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
