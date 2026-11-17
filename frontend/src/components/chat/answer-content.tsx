import { Fragment } from "react";
import { parseAnswer, type Inline } from "@/lib/utils/answer-format";
import { cn } from "@/lib/utils/cn";

interface AnswerContentProps {
  content: string;
  /** Ranks de citação válidos nesta mensagem; marcadores fora da lista viram texto. */
  ranks?: Set<number>;
  onCite?: (rank: number) => void;
}

function Inlines({ inlines, ranks, onCite }: { inlines: Inline[] } & Omit<AnswerContentProps, "content">) {
  return (
    <>
      {inlines.map((inline, i) => {
        if (inline.kind === "bold") return <strong key={i} className="font-semibold">{inline.value}</strong>;
        if (inline.kind === "text") return <Fragment key={i}>{inline.value}</Fragment>;
        const clickable = !!onCite && (!ranks || ranks.has(inline.rank));
        return (
          <button
            key={i}
            type="button"
            disabled={!clickable}
            onClick={() => onCite?.(inline.rank)}
            aria-label={`Ver fonte ${inline.rank}`}
            className={cn(
              "mx-0.5 inline-flex h-[18px] min-w-[18px] -translate-y-px items-center justify-center rounded-[5px] px-1 align-middle font-mono text-[11px] font-semibold",
              "bg-cite-soft text-cite transition-colors",
              clickable ? "hover:bg-cite hover:text-bg cursor-pointer" : "cursor-default opacity-80",
            )}
          >
            {inline.rank}
          </button>
        );
      })}
    </>
  );
}

export function AnswerContent({ content, ranks, onCite }: AnswerContentProps) {
  const blocks = parseAnswer(content);
  return (
    <div className="space-y-3 text-[15px] leading-7">
      {blocks.map((block, i) => {
        if (block.kind === "heading") {
          return (
            <p key={i} className="font-semibold text-fg">
              <Inlines inlines={block.inlines} ranks={ranks} onCite={onCite} />
            </p>
          );
        }
        if (block.kind === "list") {
          const List = block.ordered ? "ol" : "ul";
          return (
            <List key={i} className={cn("space-y-1 pl-5", block.ordered ? "list-decimal" : "list-disc")}>
              {block.items.map((item, j) => (
                <li key={j} className="pl-1 marker:text-fg-subtle">
                  <Inlines inlines={item} ranks={ranks} onCite={onCite} />
                </li>
              ))}
            </List>
          );
        }
        return (
          <p key={i}>
            <Inlines inlines={block.inlines} ranks={ranks} onCite={onCite} />
          </p>
        );
      })}
    </div>
  );
}
