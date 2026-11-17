import { validateFile } from "./validate-file";

const file = (name: string, size: number, type = "application/pdf") =>
  new File([new Uint8Array(size)], name, { type });

describe("validateFile", () => {
  it("accepts PDFs within the size limit", () => {
    expect(validateFile(file("contrato.pdf", 1024))).toBeNull();
  });

  it("accepts .pdf even when the browser reports an empty MIME type", () => {
    expect(validateFile(file("contrato.PDF", 10, ""))).toBeNull();
  });

  it("rejects other types, empty files and oversized files", () => {
    expect(validateFile(file("foto.png", 10, "image/png"))).toMatch(/PDF/);
    expect(validateFile(file("vazio.pdf", 0))).toMatch(/vazio/);
    expect(validateFile(file("grande.pdf", 26 * 1024 * 1024))).toMatch(/25 MB/);
  });
});
