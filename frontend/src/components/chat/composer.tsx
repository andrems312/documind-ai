"use client";

import { ArrowUp, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

interface ComposerProps {
  onSend: (text: string) => void;
  onStop: () => void;
  streaming: boolean;
  disabled?: boolean;
  placeholder?: string;
}

const MAX_LENGTH = 4000;

export function Composer({ onSend, onStop, streaming, disabled, placeholder }: ComposerProps) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = ref.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  }, [value]);

  function submit() {
    const text = value.trim();
    if (!text || streaming || disabled) return;
    onSend(text);
    setValue("");
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      className="rounded-xl border border-border-strong bg-surface p-2 shadow-card transition-colors focus-within:border-accent"
    >
      <label htmlFor="chat-input" className="sr-only">
        Pergunta
      </label>
      <textarea
        id="chat-input"
        ref={ref}
        rows={1}
        value={value}
        maxLength={MAX_LENGTH}
        disabled={disabled}
        placeholder={placeholder ?? "Pergunte algo sobre os documentos…"}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault();
            submit();
          }
        }}
        className="block max-h-[200px] w-full resize-none bg-transparent px-2 py-1.5 text-[15px] text-fg outline-none placeholder:text-fg-subtle disabled:opacity-60"
      />
      <div className="flex items-center justify-between gap-2 px-1 pt-1">
        <span className="text-[11px] text-fg-subtle">
          <kbd className="font-mono">Enter</kbd> envia · <kbd className="font-mono">Shift+Enter</kbd> quebra linha
        </span>
        {streaming ? (
          <Button type="button" size="icon" variant="secondary" aria-label="Parar resposta" onClick={onStop}>
            <Square className="fill-current" />
          </Button>
        ) : (
          <Button type="submit" size="icon" aria-label="Enviar pergunta" disabled={!value.trim() || disabled}>
            <ArrowUp />
          </Button>
        )}
      </div>
    </form>
  );
}
