import { Scale } from "lucide-react";
import type { Metadata } from "next";
import { ComingSoon } from "@/components/layout/coming-soon";

export const metadata: Metadata = { title: "Comparar" };

export default function ComparePage() {
  return (
    <ComingSoon
      icon={Scale}
      title="Comparar documentos"
      description="Identifique diferenças e semelhanças entre dois ou mais documentos."
      phase="FASE 4 (recursos avançados)"
    />
  );
}
