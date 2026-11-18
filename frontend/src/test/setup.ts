import "@testing-library/jest-dom/vitest";

// Valores de teste para a validação de ambiente (src/lib/env.ts), que falha no import sem eles.
process.env.NEXT_PUBLIC_SUPABASE_URL ??= "https://test.supabase.co";
process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ??= "test-anon-key";
process.env.NEXT_PUBLIC_API_URL ??= "http://localhost:8000";
