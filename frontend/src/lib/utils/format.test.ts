import { formatBytes, formatRelative, pluralize } from "./format";

describe("formatBytes", () => {
  it("formats bytes, kilobytes and megabytes in pt-BR", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1536)).toBe("1,5 KB");
    expect(formatBytes(25 * 1024 * 1024)).toBe("25 MB");
  });
});

describe("formatRelative", () => {
  const now = new Date("2026-11-17T12:00:00Z");

  it("says 'agora mesmo' for very recent dates", () => {
    expect(formatRelative("2026-11-17T11:59:50Z", now)).toBe("agora mesmo");
  });

  it("formats minutes, hours and days", () => {
    expect(formatRelative("2026-11-17T11:55:00Z", now)).toBe("há 5 minutos");
    expect(formatRelative("2026-11-17T09:00:00Z", now)).toBe("há 3 horas");
    expect(formatRelative("2026-11-16T12:00:00Z", now)).toBe("ontem");
  });
});

describe("pluralize", () => {
  it("chooses singular or plural", () => {
    expect(pluralize(1, "página", "páginas")).toBe("1 página");
    expect(pluralize(3, "página", "páginas")).toBe("3 páginas");
  });
});
