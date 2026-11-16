import type { LucideIcon } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils/cn";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-dashed border-border-strong px-6 py-14 text-center animate-rise",
        className,
      )}
    >
      <div className="relative mb-4">
        <div className="absolute inset-0 rounded-full bg-accent/20 blur-xl" aria-hidden />
        <div className="relative flex size-14 items-center justify-center rounded-2xl border border-border bg-surface shadow-card">
          <Icon className="size-6 text-accent" aria-hidden />
        </div>
      </div>
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-fg-muted">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
