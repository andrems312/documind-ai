"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { AuthHeading } from "@/components/auth/auth-heading";
import { translateAuthError } from "@/components/auth/auth-errors";
import { forgotPasswordSchema, type ForgotPasswordValues } from "@/components/auth/schemas";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase/client";

export function ForgotPasswordForm() {
  const [serverError, setServerError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordValues>({ resolver: zodResolver(forgotPasswordSchema) });

  async function onSubmit({ email }: ForgotPasswordValues) {
    setServerError(null);
    const supabase = createClient();
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/callback?next=/reset-password`,
    });
    if (error) {
      setServerError(translateAuthError(error));
      return;
    }
    setSent(true);
  }

  return (
    <>
      <AuthHeading
        title="Recuperar senha"
        description="Informe seu e-mail e enviaremos um link para definir uma nova senha."
      />
      {sent ? (
        <Alert tone="success" title="Verifique sua caixa de entrada">
          Se existir uma conta com este e-mail, você receberá o link em instantes.
        </Alert>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <Field label="E-mail" htmlFor="email" error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="voce@exemplo.com"
              invalid={!!errors.email}
              {...register("email")}
            />
          </Field>
          {serverError && <Alert tone="danger">{serverError}</Alert>}
          <Button type="submit" className="w-full" loading={isSubmitting}>
            Enviar link
          </Button>
        </form>
      )}
      <p className="mt-5 text-center text-sm text-fg-muted">
        <Link href="/login" className="text-accent hover:underline">
          Voltar para o login
        </Link>
      </p>
    </>
  );
}
