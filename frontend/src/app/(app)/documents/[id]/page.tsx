import type { Metadata } from "next";
import { Suspense } from "react";
import { DocumentDetailView } from "@/components/documents/document-detail-view";

export const metadata: Metadata = { title: "Documento" };

export default function DocumentDetailPage() {
  return (
    <Suspense>
      <DocumentDetailView />
    </Suspense>
  );
}
