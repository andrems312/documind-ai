/**
 * Localiza `needle` em `text` ignorando diferenças de espaços e quebras de linha.
 * Retorna [início, fim) em índices do texto original, ou null.
 */
export function findHighlight(text: string, needle: string): [number, number] | null {
  const target = needle.replace(/\s+/g, " ").trim();
  if (!target) return null;

  let collapsed = "";
  const map: number[] = [];
  let previousWasSpace = false;
  for (let i = 0; i < text.length; i++) {
    const isSpace = /\s/.test(text[i]!);
    if (isSpace && previousWasSpace) continue;
    collapsed += isSpace ? " " : text[i];
    map.push(i);
    previousWasSpace = isSpace;
  }

  const at = collapsed.indexOf(target);
  if (at === -1) return null;
  return [map[at]!, map[at + target.length - 1]! + 1];
}
