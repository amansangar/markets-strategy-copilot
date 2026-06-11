import { cn } from "@/lib/utils";

export function BrandLogo({ compact = false, className }: { compact?: boolean; className?: string }) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="relative flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-cyan-200/25 bg-[radial-gradient(circle_at_25%_18%,rgba(125,249,255,0.9),transparent_30%),radial-gradient(circle_at_78%_82%,rgba(16,185,129,0.55),transparent_34%),linear-gradient(135deg,#061423,#0b2338_52%,#062821)] shadow-[0_18px_42px_rgba(0,211,199,0.24)]">
        <div className="absolute inset-1 rounded-[18px] border border-white/10" />
        <svg viewBox="0 0 48 48" aria-hidden="true" className="relative h-9 w-9">
          <path d="M8 34.5H40" fill="none" stroke="#164e63" strokeWidth="2" strokeLinecap="round" />
          <path d="M11 31L17 24L22 27L28 15L36 11" fill="none" stroke="#67e8f9" strokeWidth="3.6" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M11 37L18 32L25 34L32 25L39 22" fill="none" stroke="#34d399" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" opacity="0.95" />
          <path d="M18 16V31M28 10V28M36 10V23" fill="none" stroke="#d9f99d" strokeWidth="2" strokeLinecap="round" opacity="0.75" />
          <circle cx="36" cy="11" r="4" fill="#06b6d4" />
          <circle cx="36" cy="11" r="2" fill="#ecfeff" />
        </svg>
      </div>
      {!compact ? (
        <div className="min-w-0">
          <p className="text-[10px] uppercase tracking-[0.34em] text-cyan-200/70">Markets</p>
          <h1 className="truncate text-lg font-semibold leading-tight text-white">Strategy Copilot</h1>
          <p className="text-[11px] text-slate-500">by Aman Sangar</p>
        </div>
      ) : null}
    </div>
  );
}
