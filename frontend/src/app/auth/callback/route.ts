import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

/**
 * Destino dos links de e-mail do Supabase (confirmação de cadastro e recuperação de senha).
 * Troca o `code` por uma sessão em cookies e redireciona para `next` (apenas caminhos internos).
 */
export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const rawNext = searchParams.get("next") ?? "/dashboard";
  const next = rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "/dashboard";

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  const fallback = new URL("/login", origin);
  fallback.searchParams.set("error", "link_invalido");
  return NextResponse.redirect(fallback);
}
