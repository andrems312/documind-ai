"use client";

import {
  FileText,
  LayoutDashboard,
  MessageSquareText,
  Scale,
  Search,
  Settings,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "@/components/ui/logo";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";
import { useUiStore } from "@/stores/ui";

export const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documentos", icon: FileText },
  { href: "/chat", label: "Conversas", icon: MessageSquareText },
  { href: "/compare", label: "Comparar", icon: Scale },
  { href: "/search", label: "Busca", icon: Search },
  { href: "/settings", label: "Configurações", icon: Settings },
] as const;

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Navegação principal" className="flex flex-col gap-1 px-3">
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-accent-soft text-accent"
                : "text-fg-muted hover:bg-surface-2 hover:text-fg",
            )}
          >
            <Icon className={cn("size-4", active ? "text-accent" : "text-fg-subtle group-hover:text-fg")} />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar() {
  const open = useUiStore((s) => s.sidebarOpen);
  const close = useUiStore((s) => s.closeSidebar);

  return (
    <>
      {/* Desktop */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-surface lg:flex">
        <div className="flex h-16 items-center px-5">
          <Link href="/dashboard" aria-label="Ir para o dashboard">
            <Logo />
          </Link>
        </div>
        <NavLinks />
        <div className="mt-auto p-4">
          <p className="rounded-md border border-border bg-surface-2 p-3 text-xs leading-relaxed text-fg-muted">
            Respostas sempre fundamentadas nos seus documentos, com citação de página.
          </p>
        </div>
      </aside>

      {/* Mobile drawer */}
      <div
        className={cn(
          "fixed inset-0 z-40 lg:hidden",
          open ? "pointer-events-auto" : "pointer-events-none",
        )}
        aria-hidden={!open}
      >
        <div
          onClick={close}
          className={cn(
            "absolute inset-0 bg-black/50 transition-opacity duration-200",
            open ? "opacity-100" : "opacity-0",
          )}
        />
        <aside
          className={cn(
            "absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-surface shadow-card transition-transform duration-200",
            open ? "translate-x-0" : "-translate-x-full",
          )}
          role="dialog"
          aria-label="Menu"
        >
          <div className="flex h-16 items-center justify-between px-4">
            <Logo />
            <Button variant="ghost" size="icon" aria-label="Fechar menu" onClick={close}>
              <X />
            </Button>
          </div>
          <NavLinks onNavigate={close} />
        </aside>
      </div>
    </>
  );
}
