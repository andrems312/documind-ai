import type { LucideIcon } from "lucide-react";
import { EmptyState } from "@/components/layout/empty-state";
import { PageHeader } from "@/components/layout/page-header";

interface ComingSoonProps {
  icon: LucideIcon;
  title: string;
  description: string;
  phase: string;
}

/** Página de área ainda não implementada: honesta sobre o estágio, sem simular funcionalidade. */
export function ComingSoon({ icon, title, description, phase }: ComingSoonProps) {
  return (
    <>
      <PageHeader title={title} description={description} />
      <EmptyState
        icon={icon}
        title="Em construção"
        description={`Esta área será implementada na ${phase}.`}
      />
    </>
  );
}
