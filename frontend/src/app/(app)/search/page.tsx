import { Search } from "lucide-react";
import type { Metadata } from "next";
import { ComingSoon } from "@/components/layout/coming-soon";

export const metadata: Metadata = { title: "Busca" };

export default function SearchPage() {
  return (
    <ComingSoon
      icon={Search}
      title="Busca semântica"
      description="Encontre trechos por significado em toda a sua biblioteca."
      phase="FASE 4 (recursos avançados)"
    />
  );
}
