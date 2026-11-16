import { cn } from "@/lib/utils/cn";

interface LogoProps {
  className?: string;
  withText?: boolean;
}

/** Marca do DocuMind AI: um documento cujo conteúdo vira um nó de conhecimento. */
export function Logo({ className, withText = true }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <svg
        viewBox="0 0 32 32"
        className="size-8 shrink-0"
        aria-hidden
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <rect width="32" height="32" rx="9" className="fill-accent" />
        <path
          d="M10 8.5h8l4 4V23.5a1 1 0 0 1-1 1H10a1 1 0 0 1-1-1v-14a1 1 0 0 1 1-1Z"
          className="stroke-white/90"
          strokeWidth="1.6"
          strokeLinejoin="round"
        />
        <path d="M18 8.5v4h4" className="stroke-white/90" strokeWidth="1.6" strokeLinejoin="round" />
        <circle cx="13" cy="15.5" r="1.4" className="fill-cite" />
        <circle cx="19" cy="18.5" r="1.4" className="fill-cite" />
        <circle cx="13.5" cy="21" r="1.4" className="fill-cite" />
        <path
          d="M13 15.5l6 3M19 18.5l-5.5 2.5"
          className="stroke-cite"
          strokeWidth="1.2"
          strokeLinecap="round"
        />
      </svg>
      {withText && (
        <span className="whitespace-nowrap text-[15px] font-semibold tracking-tight text-fg">
          DocuMind<span className="text-accent"> AI</span>
        </span>
      )}
    </span>
  );
}
