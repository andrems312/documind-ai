import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

// CSP conservadora: trava base-uri, form-action e enquadramento (anticlickjacking) sem
// restringir origens de script/estilo — o que poderia quebrar o Next. Endurecer depois com nonce.
const CSP = "base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "Content-Security-Policy", value: CSP },
  ...(isProd
    ? [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" }]
    : []),
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // `standalone` é usado pela imagem Docker; em dev no Windows exige permissão de symlink.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  poweredByHeader: false,
  headers: async () => [{ source: "/(.*)", headers: securityHeaders }],
};

export default nextConfig;
