import { FileSearch, FileText, Scale } from "lucide-react";
import type { AnalysisType } from "@/types/api";

export const ANALYSIS_META: Record<
  AnalysisType,
  { label: string; icon: typeof FileText; verb: string }
> = {
  summary: { label: "Resumo", icon: FileText, verb: "Resumir" },
  key_info: { label: "Informações-chave", icon: FileSearch, verb: "Extrair informações" },
  comparison: { label: "Comparação", icon: Scale, verb: "Comparar" },
};
