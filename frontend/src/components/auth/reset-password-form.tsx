"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { AuthHeading } from "@/components/auth/auth-heading";
import { translateAuthError } from "@/components/auth/auth-errors";
import { resetPasswordSchema, type ResetPasswordValues } from "@/components/auth/schemas";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { createClient } from "@/lib/supabase/client";

type SessionState = "checking" | "ready" | "missing";

export function ResetPasswordForm() {
  const router = useRouter();
  const [sessionState, setSessionState] = useState<SessionState>("checking");
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordValues>({ resolver: zodResolver(resetPasswordSchema) });

  // O link de recuperação cria uma sessão temporária via /auth/callback; sem ela não há o que fazer.
  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data }) => {
      setSessionState(data.user ? "ready" : "missing");
    });
  }, []);

  async function onSubmit({ password }: ResetPasswordValues) {
    setServerError(null);
    const supabase = createClient();
    const { error } = await supabase.auth.updateUser({ password });
    if (error) {
      setServerError(translateAuthError(error));
      return;
    }
    await supabase.auth.signOut();
    router.replace("/login?reset=ok");
    router.refresh();
  }

  return (
    <>
      <AuthHeading title="Definir nova senha" description="Escolha uma senha forte que você ainda não usou aqui." />
      {sessionState === "checking" && (
        <div className="space-y-4" aria-busy>
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      )}
      {sessionState === "missing" && (
        <div className="space-y-4">
          <Alert tone="danger" title="Link inválido ou expirado">
            Solicite uma nova recuperação de senha para continuar.
          </Alert>
          <Button asChild variant="outline" className="w-full">
            <Link href="/forgot-password">Solicitar novo link</Link>
          </Button>
        </div>
      )}
      {sessionState === "ready" && (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <Field label="Nova senha" htmlFor="password" error={errors.password?.message} hint="Mínimo de 8 caracteres.">
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              invalid={!!errors.password}
              {...register("password")}
            />
          </Field>
          <Field label="Confirmar nova senha" htmlFor="confirmPassword" error={errors.confirmPassword?.message}>
            <Input
              id="confirmPassword"
              type="password"
              autoComplete="new-password"
              invalid={!!errors.confirmPassword}
              {...register("confirmPassword")}
            />
          </Field>
          {serverError && <Alert tone="danger">{serverError}</Alert>}
          <Button type="submit" className="w-full" loading={isSubmitting}>
            Salvar nova senha
          </Button>
        </form>
      )}
    </>
  );
}
