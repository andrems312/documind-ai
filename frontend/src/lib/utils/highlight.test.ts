import { findHighlight } from "./highlight";

describe("findHighlight", () => {
  const text = "Cláusula 2. O prazo de vigência\n\ndeste contrato é de 24 meses.";

  it("finds an exact excerpt", () => {
    const range = findHighlight(text, "O prazo de vigência");
    expect(range).not.toBeNull();
    expect(text.slice(...range!)).toBe("O prazo de vigência");
  });

  it("ignores whitespace differences between excerpt and page", () => {
    const range = findHighlight(text, "vigência deste   contrato");
    expect(text.slice(...range!)).toBe("vigência\n\ndeste contrato");
  });

  it("returns null when not found or empty", () => {
    expect(findHighlight(text, "multa rescisória")).toBeNull();
    expect(findHighlight(text, "   ")).toBeNull();
  });
});
