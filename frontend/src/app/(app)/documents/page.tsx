import { FileText } from "lucide-react";
import type { Metadata } from "next";
import { ComingSoon } from "@/components/layout/coming-soon";

export const metadata: Metadata = { title: "Documentos" };

export default function DocumentsPage() {
  return (
    <ComingSoon
      icon={FileText}
      title="Documentos"
      description="Envie, organize e acompanhe o processamento dos seus PDFs."
      phase="FASE 3 (upload, extração e embeddings)"
    />
  );
}
