"use client";

import { useQueryClient } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe } from "@/hooks/use-me";
import { createClient } from "@/lib/supabase/client";

function initials(name: string | null | undefined, email: string | null | undefined): string {
  const source = name?.trim() || email?.split("@")[0] || "?";
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

export function UserMenu({ email }: { email: string | null }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: me, isPending } = useMe();
  const [signingOut, setSigningOut] = useState(false);

  async function signOut() {
    setSigningOut(true);
    const supabase = createClient();
    const { error } = await supabase.auth.signOut();
    if (error) {
      toast.error("Não foi possível sair. Tente novamente.");
      setSigningOut(false);
      return;
    }
    queryClient.clear();
    router.replace("/login");
    router.refresh();
  }

  return (
    <div className="flex items-center gap-2">
      <div className="hidden items-center gap-2.5 sm:flex">
        <div className="flex size-8 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">
          {initials(me?.full_name, me?.email ?? email)}
        </div>
        <div className="leading-tight">
          {isPending ? (
            <>
              <Skeleton className="mb-1 h-3 w-24" />
              <Skeleton className="h-2.5 w-32" />
            </>
          ) : (
            <>
              <p className="text-sm font-medium">{me?.full_name ?? "Sem nome"}</p>
              <p className="text-xs text-fg-subtle">{me?.email ?? email}</p>
            </>
          )}
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        aria-label="Sair"
        title="Sair"
        onClick={signOut}
        loading={signingOut}
      >
        {!signingOut && <LogOut />}
      </Button>
    </div>
  );
}
