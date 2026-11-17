const sizeFormatter = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${sizeFormatter.format(value)} ${units[unit]}`;
}

const relative = new Intl.RelativeTimeFormat("pt-BR", { numeric: "auto" });
const STEPS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["second", 60],
  ["minute", 60],
  ["hour", 24],
  ["day", 7],
  ["week", 4.35],
  ["month", 12],
  ["year", Number.POSITIVE_INFINITY],
];

export function formatRelative(iso: string, now: Date = new Date()): string {
  let value = (new Date(iso).getTime() - now.getTime()) / 1000;
  for (const [unit, size] of STEPS) {
    if (Math.abs(value) < size) {
      if (unit === "second" && Math.abs(value) < 45) return "agora mesmo";
      return relative.format(Math.round(value), unit);
    }
    value /= size;
  }
  return relative.format(Math.round(value), "year");
}

export function pluralize(count: number, singular: string, plural: string): string {
  return `${count} ${count === 1 ? singular : plural}`;
}
