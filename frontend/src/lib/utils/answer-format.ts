/**
 * Formatação leve das respostas do modelo, convertida em estrutura (não em HTML), para que o
 * React renderize com segurança: parágrafos, listas, títulos simples, **negrito** e citações [n].
 */

export type Inline =
  | { kind: "text"; value: string }
  | { kind: "bold"; value: string }
  | { kind: "cite"; rank: number };

export type Block =
  | { kind: "paragraph"; inlines: Inline[] }
  | { kind: "heading"; inlines: Inline[] }
  | { kind: "list"; ordered: boolean; items: Inline[][] };

const INLINE = /(\*\*[^*\n]+\*\*|\[\d{1,3}\])/g;
const BULLET = /^\s*[-*•]\s+/;
const NUMBERED = /^\s*\d+[.)]\s+/;
const HEADING = /^\s*#{1,6}\s+/;

export function parseInline(text: string): Inline[] {
  const result: Inline[] = [];
  for (const part of text.split(INLINE)) {
    if (!part) continue;
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      result.push({ kind: "bold", value: part.slice(2, -2) });
    } else if (/^\[\d{1,3}\]$/.test(part)) {
      result.push({ kind: "cite", rank: Number(part.slice(1, -1)) });
    } else {
      result.push({ kind: "text", value: part });
    }
  }
  return result;
}

export function parseAnswer(content: string): Block[] {
  const blocks: Block[] = [];
  for (const chunk of content.replace(/\r/g, "").split(/\n{2,}/)) {
    const lines = chunk.split("\n").filter((line) => line.trim());
    if (lines.length === 0) continue;

    let paragraph: string[] = [];
    let list: { ordered: boolean; items: Inline[][] } | null = null;
    const flushParagraph = () => {
      if (paragraph.length) blocks.push({ kind: "paragraph", inlines: parseInline(paragraph.join(" ")) });
      paragraph = [];
    };
    const flushList = () => {
      if (list) blocks.push({ kind: "list", ...list });
      list = null;
    };

    for (const line of lines) {
      const bullet = BULLET.test(line);
      const numbered = NUMBERED.test(line);
      if (bullet || numbered) {
        flushParagraph();
        if (!list || list.ordered !== numbered) {
          flushList();
          list = { ordered: numbered, items: [] };
        }
        list.items.push(parseInline(line.replace(bullet ? BULLET : NUMBERED, "")));
      } else if (HEADING.test(line)) {
        flushParagraph();
        flushList();
        blocks.push({ kind: "heading", inlines: parseInline(line.replace(HEADING, "")) });
      } else if (list) {
        // linha de continuação do último item da lista
        list.items[list.items.length - 1]!.push({ kind: "text", value: ` ${line.trim()}` });
      } else {
        paragraph.push(line.trim());
      }
    }
    flushParagraph();
    flushList();
  }
  return blocks;
}
