import Link from "next/link";
import { Logo } from "@/components/ui/logo";
import { ThemeToggle } from "@/components/layout/theme-toggle";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-dvh flex-col bg-grid">
      <div
        className="pointer-events-none absolute -top-32 left-1/2 h-[360px] w-[600px] -translate-x-1/2 rounded-full bg-accent/20 blur-[110px]"
        aria-hidden
      />
      <header className="relative flex items-center justify-between px-6 py-5">
        <Link href="/" aria-label="Página inicial">
          <Logo />
        </Link>
        <ThemeToggle />
      </header>
      <main className="relative flex flex-1 items-center justify-center px-4 pb-16">
        <div className="w-full max-w-md rounded-xl border border-border bg-surface p-6 shadow-card animate-rise sm:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
