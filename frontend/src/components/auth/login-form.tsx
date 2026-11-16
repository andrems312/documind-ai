"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { AuthHeading } from "@/components/auth/auth-heading";
import { translateAuthError } from "@/components/auth/auth-errors";
import { loginSchema, type LoginValues } from "@/components/auth/schemas";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase/client";

function safeNext(value: string | null): string {
  // Evita open redirect: só caminhos internos.
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/dashboard";
}

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(values: LoginValues) {
    setServerError(null);
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithPassword(values);
    if (error) {
      setServerError(translateAuthError(error));
      return;
    }
    router.replace(safeNext(params.get("next")));
    router.refresh();
  }

  return (
    <>
      <AuthHeading title="Bem-vindo de volta" description="Entre para continuar conversando com seus documentos." />
      {params.get("reset") === "ok" && (
        <Alert tone="success" className="mb-4">
          Senha atualizada. Entre com a nova senha.
        </Alert>
      )}
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
        <Field label="Senha" htmlFor="password" error={errors.password?.message}>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            invalid={!!errors.password}
            {...register("password")}
          />
        </Field>
        {serverError && <Alert tone="danger">{serverError}</Alert>}
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Entrar
        </Button>
      </form>
      <div className="mt-5 flex flex-col gap-2 text-center text-sm text-fg-muted">
        <Link href="/forgot-password" className="text-accent hover:underline">
          Esqueci minha senha
        </Link>
        <p>
          Não tem conta?{" "}
          <Link href="/register" className="font-medium text-accent hover:underline">
            Criar conta
          </Link>
        </p>
      </div>
    </>
  );
}
