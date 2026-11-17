import { readSSE } from "./sse";

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  });
}

async function collect(chunks: string[]) {
  const events: unknown[] = [];
  for await (const event of readSSE(streamOf(chunks))) events.push(event);
  return events;
}

describe("readSSE", () => {
  it("parses complete events", async () => {
    const events = await collect(['data: {"type":"token","delta":"Olá"}\n\n', 'data: {"type":"done"}\n\n']);
    expect(events).toEqual([{ type: "token", delta: "Olá" }, { type: "done" }]);
  });

  it("joins events split across network chunks", async () => {
    const events = await collect(['data: {"type":"tok', 'en","delta":"a"}\n', "\n"]);
    expect(events).toEqual([{ type: "token", delta: "a" }]);
  });

  it("ignores comments and handles CRLF and a trailing event without blank line", async () => {
    const events = await collect([": keep-alive\r\n\r\n", 'data: {"n":1}\r\n\r\n', 'data: {"n":2}']);
    expect(events).toEqual([{ n: 1 }, { n: 2 }]);
  });

  it("decodes multi-byte characters split between chunks", async () => {
    const bytes = new TextEncoder().encode('data: {"t":"ação"}\n\n');
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(bytes.slice(0, 15));
        controller.enqueue(bytes.slice(15));
        controller.close();
      },
    });
    const events: unknown[] = [];
    for await (const event of readSSE(stream)) events.push(event);
    expect(events).toEqual([{ t: "ação" }]);
  });
});
