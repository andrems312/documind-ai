import type { AuthError } from "@supabase/supabase-js";

/** Traduz as mensagens mais comuns do Supabase Auth para português. */
export function translateAuthError(error: AuthError | null | undefined): string {
  const message = error?.message?.toLowerCase() ?? "";
  if (message.includes("invalid login credentials")) return "E-mail ou senha incorretos.";
  if (message.includes("email not confirmed")) return "Confirme seu e-mail antes de entrar.";
  if (message.includes("user already registered")) return "Já existe uma conta com este e-mail.";
  if (message.includes("password should be at least")) return "A senha é muito curta.";
  if (message.includes("rate limit") || message.includes("too many requests"))
    return "Muitas tentativas. Aguarde um instante e tente novamente.";
  if (message.includes("same password"))
    return "A nova senha precisa ser diferente da anterior.";
  if (message.includes("session") && message.includes("missing"))
    return "Link expirado ou inválido. Solicite uma nova recuperação de senha.";
  return error?.message ?? "Algo deu errado. Tente novamente.";
}
