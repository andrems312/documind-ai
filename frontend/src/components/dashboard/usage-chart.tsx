"use client";

import { useId } from "react";
import type { UsagePoint } from "@/types/api";
import { formatCompact } from "@/lib/utils/format";

const WIDTH = 640;
const HEIGHT = 160;
const PAD_X = 8;
const PAD_TOP = 12;
const PAD_BOTTOM = 22;

function dayLabel(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}

/** Gráfico de barras (SVG, sem dependências) dos tokens por dia nas últimas duas semanas. */
export function UsageChart({ data }: { data: UsagePoint[] }) {
  const titleId = useId();
  const totals = data.map((p) => p.prompt_tokens + p.completion_tokens);
  const max = Math.max(1, ...totals);
  const plotW = WIDTH - PAD_X * 2;
  const plotH = HEIGHT - PAD_TOP - PAD_BOTTOM;
  const slot = plotW / data.length;
  const barW = Math.min(28, slot * 0.6);
  const hasData = totals.some((t) => t > 0);

  return (
    <figure className="w-full">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="h-40 w-full"
        role="img"
        aria-labelledby={titleId}
        preserveAspectRatio="none"
      >
        <title id={titleId}>Tokens consumidos por dia nos últimos 14 dias</title>
        <line
          x1={PAD_X}
          y1={PAD_TOP + plotH}
          x2={WIDTH - PAD_X}
          y2={PAD_TOP + plotH}
          stroke="var(--border)"
          strokeWidth={1}
        />
        {data.map((point, i) => {
          const total = point.prompt_tokens + point.completion_tokens;
          const height = hasData ? (total / max) * plotH : 0;
          const x = PAD_X + slot * i + (slot - barW) / 2;
          const y = PAD_TOP + plotH - height;
          const showLabel = i % 2 === 0 || i === data.length - 1;
          return (
            <g key={point.day}>
              <rect
                x={x}
                y={height > 0 ? y : PAD_TOP + plotH - 1}
                width={barW}
                height={Math.max(height, total > 0 ? 2 : 0)}
                rx={3}
                fill="var(--accent)"
                opacity={total > 0 ? 0.9 : 0.15}
              >
                <title>
                  {dayLabel(point.day)}: {total.toLocaleString("pt-BR")} tokens ({point.events} evento
                  {point.events === 1 ? "" : "s"})
                </title>
              </rect>
              {showLabel && (
                <text
                  x={x + barW / 2}
                  y={HEIGHT - 6}
                  textAnchor="middle"
                  className="fill-[var(--fg-subtle)] text-[9px]"
                >
                  {dayLabel(point.day)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-1 flex justify-between text-xs text-fg-subtle">
        <span>Tokens por dia (14 dias)</span>
        <span>pico: {formatCompact(max)}</span>
      </figcaption>
    </figure>
  );
}
