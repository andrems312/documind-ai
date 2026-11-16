import { FileQuestion } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/layout/empty-state";

export default function NotFound() {
  return (
    <main className="flex min-h-dvh items-center justify-center p-6">
      <EmptyState
        icon={FileQuestion}
        title="Página não encontrada"
        description="O endereço pode estar errado ou a página foi movida."
        action={
          <Button asChild>
            <Link href="/dashboard">Voltar ao início</Link>
          </Button>
        }
        className="w-full max-w-md border-none"
      />
    </main>
  );
}
