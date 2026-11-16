import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils/cn";

type Tone = "info" | "success" | "danger";

const tones: Record<Tone, { className: string; Icon: typeof Info }> = {
  info: { className: "border-accent/30 bg-accent-soft text-fg", Icon: Info },
  success: { className: "border-success/30 bg-success/10 text-fg", Icon: CheckCircle2 },
  danger: { className: "border-danger/30 bg-danger-soft text-fg", Icon: AlertCircle },
};

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  tone?: Tone;
  title?: string;
}

export function Alert({ tone = "info", title, className, children, ...props }: AlertProps) {
  const { className: toneClass, Icon } = tones[tone];
  return (
    <div
      role={tone === "danger" ? "alert" : "status"}
      className={cn("flex gap-3 rounded-md border p-3 text-sm animate-fade-in", toneClass, className)}
      {...props}
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div className="space-y-0.5">
        {title && <p className="font-medium">{title}</p>}
        <div className="text-fg-muted">{children}</div>
      </div>
    </div>
  );
}
