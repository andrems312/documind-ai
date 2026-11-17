import { parseAnswer, parseInline } from "./answer-format";

describe("parseInline", () => {
  it("extracts bold text and citation markers", () => {
    expect(parseInline("O prazo é **24 meses** [2].")).toEqual([
      { kind: "text", value: "O prazo é " },
      { kind: "bold", value: "24 meses" },
      { kind: "text", value: " " },
      { kind: "cite", rank: 2 },
      { kind: "text", value: "." },
    ]);
  });

  it("keeps html-like text as plain text", () => {
    expect(parseInline("<script>alert(1)</script>")).toEqual([
      { kind: "text", value: "<script>alert(1)</script>" },
    ]);
  });
});

describe("parseAnswer", () => {
  it("splits paragraphs and joins soft line breaks", () => {
    const blocks = parseAnswer("Primeira linha\ncontinua.\n\nSegundo parágrafo [1].");
    expect(blocks).toHaveLength(2);
    expect(blocks[0]).toEqual({ kind: "paragraph", inlines: [{ kind: "text", value: "Primeira linha continua." }] });
    expect(blocks[1]!.kind).toBe("paragraph");
  });

  it("parses bullet and numbered lists", () => {
    const blocks = parseAnswer("Obrigações:\n- Pagar até o dia 5 [1]\n- Manter sigilo\n\n1. Primeiro\n2. Segundo");
    expect(blocks.map((b) => b.kind)).toEqual(["paragraph", "list", "list"]);
    const bullets = blocks[1] as Extract<(typeof blocks)[number], { kind: "list" }>;
    expect(bullets.ordered).toBe(false);
    expect(bullets.items).toHaveLength(2);
    expect((blocks[2] as typeof bullets).ordered).toBe(true);
  });

  it("parses markdown headings", () => {
    expect(parseAnswer("## Resumo\nTexto")[0]).toEqual({
      kind: "heading",
      inlines: [{ kind: "text", value: "Resumo" }],
    });
  });
});
