"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { MailCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { AuthHeading } from "@/components/auth/auth-heading";
import { translateAuthError } from "@/components/auth/auth-errors";
import { registerSchema, type RegisterValues } from "@/components/auth/schemas";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase/client";

export function RegisterForm() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({ resolver: zodResolver(registerSchema) });

  async function onSubmit(values: RegisterValues) {
    setServerError(null);
    const supabase = createClient();
    const { data, error } = await supabase.auth.signUp({
      email: values.email,
      password: values.password,
      options: {
        data: { full_name: values.fullName },
        emailRedirectTo: `${window.location.origin}/auth/callback?next=/dashboard`,
      },
    });
    if (error) {
      setServerError(translateAuthError(error));
      return;
    }
    // Com confirmação de e-mail ativa, não há sessão ainda: orientar o usuário.
    if (!data.session) {
      setSentTo(values.email);
      return;
    }
    router.replace("/dashboard");
    router.refresh();
  }

  if (sentTo) {
    return (
      <div className="text-center animate-fade-in">
        <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-full bg-accent-soft">
          <MailCheck className="size-6 text-accent" aria-hidden />
        </div>
        <h1 className="text-xl font-semibold">Confirme seu e-mail</h1>
        <p className="mt-2 text-sm text-fg-muted">
          Enviamos um link de confirmação para <span className="font-medium text-fg">{sentTo}</span>.
          Abra-o para ativar sua conta.
        </p>
        <Button asChild variant="outline" className="mt-6">
          <Link href="/login">Voltar para o login</Link>
        </Button>
      </div>
    );
  }

  return (
    <>
      <AuthHeading title="Criar sua conta" description="Leva menos de um minuto." />
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <Field label="Nome" htmlFor="fullName" error={errors.fullName?.message}>
          <Input
            id="fullName"
            autoComplete="name"
            placeholder="Como quer ser chamado"
            invalid={!!errors.fullName}
            {...register("fullName")}
          />
        </Field>
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
        <Field
          label="Senha"
          htmlFor="password"
          error={errors.password?.message}
          hint="Mínimo de 8 caracteres."
        >
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            invalid={!!errors.password}
            {...register("password")}
          />
        </Field>
        <Field label="Confirmar senha" htmlFor="confirmPassword" error={errors.confirmPassword?.message}>
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
          Criar conta
        </Button>
      </form>
      <p className="mt-5 text-center text-sm text-fg-muted">
        Já tem conta?{" "}
        <Link href="/login" className="font-medium text-accent hover:underline">
          Entrar
        </Link>
      </p>
    </>
  );
}
