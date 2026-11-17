"use client";

import { X } from "lucide-react";
import * as React from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils/cn";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

/**
 * Modal acessível sobre o elemento nativo <dialog>: foco preso, Esc para fechar e fundo inerte
 * vêm do navegador. Clique fora do conteúdo também fecha.
 */
export function Dialog({ open, onClose, title, description, children, footer, className }: DialogProps) {
  const ref = React.useRef<HTMLDialogElement>(null);
  const titleId = React.useId();
  const descriptionId = React.useId();

  React.useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      aria-describedby={description ? descriptionId : undefined}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
      className={cn(
        "m-auto w-[calc(100%-2rem)] max-w-lg rounded-xl border border-border bg-surface p-0 text-fg shadow-card",
        "backdrop:bg-black/50 backdrop:backdrop-blur-[2px] open:animate-rise",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-4 p-5 pb-0">
        <div>
          <h2 id={titleId} className="text-base font-semibold">
            {title}
          </h2>
          {description && (
            <p id={descriptionId} className="mt-1 text-sm text-fg-muted">
              {description}
            </p>
          )}
        </div>
        <Button variant="ghost" size="icon" aria-label="Fechar" onClick={onClose} className="-mr-2 -mt-1">
          <X />
        </Button>
      </div>
      {children && <div className="p-5">{children}</div>}
      {footer && (
        <div className="flex flex-col-reverse gap-2 border-t border-border p-4 sm:flex-row sm:justify-end">
          {footer}
        </div>
      )}
    </dialog>
  );
}
