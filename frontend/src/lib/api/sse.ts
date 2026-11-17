const EVENT_SEPARATOR = /\r?\n\r?\n/;

/**
 * Leitor de Server-Sent Events a partir de um ReadableStream (resposta de `fetch`).
 * Suporta eventos divididos entre pacotes de rede, múltiplas linhas `data:` e comentários.
 */
export async function* readSSE<T = unknown>(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<T> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const parse = (block: string): T | null => {
    const data = block
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).replace(/^ /, ""))
      .join("\n");
    if (!data) return null;
    return JSON.parse(data) as T;
  };

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let match = EVENT_SEPARATOR.exec(buffer);
      while (match) {
        const block = buffer.slice(0, match.index);
        buffer = buffer.slice(match.index + match[0].length);
        const event = parse(block);
        if (event !== null) yield event;
        match = EVENT_SEPARATOR.exec(buffer);
      }
    }
    buffer += decoder.decode();
    const last = parse(buffer.trim());
    if (last !== null) yield last;
  } finally {
    reader.releaseLock();
  }
}
