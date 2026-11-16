"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { meQueryKey, useMe } from "@/hooks/use-me";
import { apiFetch } from "@/lib/api/client";
import type { Profile, ProfileUpdate } from "@/types/api";

const profileSchema = z.object({
  full_name: z.string().trim().min(2, "Informe seu nome.").max(120),
});
type ProfileValues = z.infer<typeof profileSchema>;

export function SettingsView() {
  const me = useMe();
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<ProfileValues>({ resolver: zodResolver(profileSchema), defaultValues: { full_name: "" } });

  useEffect(() => {
    if (me.data) reset({ full_name: me.data.full_name ?? "" });
  }, [me.data, reset]);

  const mutation = useMutation({
    mutationFn: (payload: ProfileUpdate) =>
      apiFetch<Profile>("/api/v1/me", { method: "PATCH", body: JSON.stringify(payload) }),
    onSuccess: (profile) => {
      queryClient.setQueryData(meQueryKey, profile);
      reset({ full_name: profile.full_name ?? "" });
      toast.success("Perfil atualizado.");
    },
    onError: (error: Error) => toast.error(error.message),
  });

  return (
    <>
      <PageHeader title="Configurações" description="Seu perfil e preferências." />
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>Perfil</CardTitle>
          <CardDescription>Como você aparece no DocuMind AI.</CardDescription>
        </CardHeader>
        <CardContent>
          {me.isPending ? (
            <div className="space-y-4" aria-busy>
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : (
            <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="space-y-4" noValidate>
              <Field label="E-mail" htmlFor="email" hint="O e-mail é gerenciado pela autenticação.">
                <Input id="email" value={me.data?.email ?? ""} disabled readOnly />
              </Field>
              <Field label="Nome" htmlFor="full_name" error={errors.full_name?.message}>
                <Input id="full_name" invalid={!!errors.full_name} {...register("full_name")} />
              </Field>
              <Button type="submit" loading={mutation.isPending} disabled={!isDirty}>
                Salvar
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </>
  );
}
