import { MessageSquareText } from "lucide-react";
import type { Metadata } from "next";
import { ComingSoon } from "@/components/layout/coming-soon";

export const metadata: Metadata = { title: "Conversas" };

export default function ChatPage() {
  return (
    <ComingSoon
      icon={MessageSquareText}
      title="Conversas"
      description="Pergunte aos seus documentos e receba respostas com a página de origem."
      phase="FASE 3 (RAG e chat com citações)"
    />
  );
}
