import { cn } from "@/lib/utils/cn";

interface ProgressProps {
  /** Valor entre 0 e 1. Sem valor = indeterminado (animação contínua). */
  value?: number;
  label: string;
  className?: string;
}

export function Progress({ value, label, className }: ProgressProps) {
  const percent = value === undefined ? undefined : Math.round(Math.min(Math.max(value, 0), 1) * 100);
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
      className={cn("h-1.5 w-full overflow-hidden rounded-full bg-surface-3", className)}
    >
      <div
        className={cn(
          "h-full rounded-full bg-accent transition-[width] duration-500 ease-out",
          percent === undefined && "w-1/3 animate-pulse",
        )}
        style={percent === undefined ? undefined : { width: `${Math.max(percent, 4)}%` }}
      />
    </div>
  );
}
