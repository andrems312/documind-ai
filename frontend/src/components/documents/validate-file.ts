import { MAX_UPLOAD_BYTES, MAX_UPLOAD_MB } from "@/lib/constants";

/** Validação imediata no navegador; o backend repete todas as checagens (e algumas a mais). */
export function validateFile(file: File): string | null {
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) return "Apenas arquivos PDF são aceitos.";
  if (file.size === 0) return "O arquivo está vazio.";
  if (file.size > MAX_UPLOAD_BYTES) return `O arquivo excede ${MAX_UPLOAD_MB} MB.`;
  return null;
}
