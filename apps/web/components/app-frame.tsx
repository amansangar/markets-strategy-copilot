"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { BrandLogo } from "@/components/brand-logo";
import { FirstRunTutorial } from "@/components/first-run-tutorial";
import { IconBell, IconChart, IconGauge, IconShield, IconSignal, IconTrendDown, IconTrendUp } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { useMarketMode } from "@/lib/use-market-mode";

const navGroups = [
  {
    label: "Research",
    items: [
      { href: "/", label: "Dashboard", icon: IconChart },
      { href: "/asset/SPY", label: "Asset Research", icon: IconChart },
      { href: "/scanner", label: "Scanner", icon: IconSignal },
    ],
  },
  {
    label: "Plan",
    items: [
      { href: "/strategy-tester", label: "Strategy Tester", icon: IconTrendUp },
      { href: "/portfolio", label: "Portfolio", icon: IconGauge },
      { href: "/reports", label: "Reports", icon: IconTrendDown },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/settings", label: "Settings", icon: IconShield },
    ],
  },
];

const mobileNavItems = [
  { href: "/", label: "Home", icon: IconChart },
  { href: "/asset/SPY", label: "Asset", icon: IconChart },
  { href: "/scanner", label: "Scan", icon: IconSignal },
  { href: "/strategy-tester", label: "Test", icon: IconTrendUp },
  { href: "/portfolio", label: "Portfolio", icon: IconGauge },
  { href: "/reports", label: "Reports", icon: IconTrendDown },
];

const mobileMoreItems = [
  { href: "/alerts", label: "Alerts", icon: IconBell },
  { href: "/workspace", label: "Workspace", icon: IconShield },
  { href: "/assistant", label: "Ask AI", icon: IconSignal },
  { href: "/pro-terminal", label: "Research Toolkit", icon: IconGauge },
  { href: "/setup", label: "Setup", icon: IconTrendUp },
  { href: "/settings", label: "Settings", icon: IconShield },
];

export function AppFrame({
  title,
  eyebrow,
  subtitle,
  actions,
  children,
  showContextStrip = true,
  showFirstRun = false,
}: {
  title: string;
  eyebrow: string;
  subtitle: string;
  actions?: ReactNode;
  children: ReactNode;
  showContextStrip?: boolean;
  showFirstRun?: boolean;
}) {
  const pathname = usePathname();
  const [mode] = useMarketMode();
  const [mobileMoreOpen, setMobileMoreOpen] = useState(false);
  const showFirstRunTutorial = showFirstRun || pathname === "/setup";

  useEffect(() => {
    setMobileMoreOpen(false);
  }, [pathname]);

  return (
    <div className="min-h-screen px-3 pb-[calc(7rem_+_env(safe-area-inset-bottom))] pt-3 md:px-6 md:pb-6 md:pt-6">
      <div className="mx-auto flex min-h-[calc(100vh_-_2rem)] max-w-[1600px] gap-4">
        <aside className="hidden w-[248px] shrink-0 lg:block">
          <Card className="flex h-full flex-col gap-6 p-5">
            <div className="space-y-4">
              <Link
                href="/"
                aria-label="Go to Markets Strategy Copilot dashboard"
                className="block rounded-[26px] outline-none transition hover:scale-[1.01] focus-visible:ring-2 focus-visible:ring-cyan-300/60"
              >
                <BrandLogo />
              </Link>
              <div className="rounded-[24px] border border-cyan-300/10 bg-cyan-300/6 p-4">
                <Badge className="mb-3 border-cyan-300/20 bg-cyan-300/10 text-cyan-100">Research App</Badge>
                <p className="text-sm leading-6 text-slate-300">
                  Find setups, understand the signal, test the idea, then save a clear investment note.
                </p>
              </div>
            </div>

            <nav className="space-y-5">
              {navGroups.map((group) => (
                <div key={group.label} className="space-y-2">
                  <p className="px-3 text-[10px] font-semibold uppercase tracking-[0.26em] text-slate-500">{group.label}</p>
                  {group.items.map((item) => {
                    const Icon = item.icon;
                    const active = pathname === item.href;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                          "flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm transition",
                          active
                            ? "border-cyan-300/20 bg-cyan-300/10 text-white shadow-[0_12px_24px_rgba(0,0,0,0.18)]"
                            : "border-transparent bg-white/0 text-slate-300 hover:border-white/8 hover:bg-white/5",
                        )}
                      >
                        <Icon className="h-4 w-4" />
                        <span>{item.label}</span>
                      </Link>
                    );
                  })}
                </div>
              ))}
            </nav>

            <div className="mt-auto rounded-[24px] border border-white/8 bg-white/4 p-4">
              <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Reminder</p>
              <p className="mt-2 text-sm leading-6 text-slate-300">
                Decision support only. No order execution, no hidden model claims, and no silent live-feed failures.
              </p>
            </div>
          </Card>
        </aside>

        <main className="min-w-0 flex-1">
          <Card className="h-full p-4 md:p-5">
            <header className="flex flex-col gap-4 border-b border-white/8 pb-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <Link
                    href="/"
                    aria-label="Go to Markets Strategy Copilot dashboard"
                    className="mb-4 flex w-fit items-center gap-3 rounded-2xl transition hover:scale-[1.01] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/60 lg:hidden"
                  >
                    <BrandLogo compact />
                    <span className="text-sm font-semibold text-white">Markets Strategy Copilot</span>
                  </Link>
                  <p className="text-[11px] uppercase tracking-[0.26em] text-slate-500">{eyebrow}</p>
                  <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white md:mt-2 md:text-3xl">{title}</h1>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{subtitle}</p>
                </div>
                <div className="flex flex-wrap items-center justify-end gap-2">
                  <button
                    type="button"
                    aria-label="Open app search"
                    onClick={() => window.dispatchEvent(new Event("markets:open-command-palette"))}
                    className="hidden h-8 items-center justify-center gap-2 rounded-full border border-cyan-300/15 bg-cyan-300/8 px-3 text-sm font-medium text-cyan-50 transition-all duration-200 hover:border-cyan-200/30 hover:bg-cyan-300/14 sm:inline-flex"
                  >
                    Search
                    <span className="rounded-full border border-white/10 bg-white/6 px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] text-slate-300">
                      Ctrl K
                    </span>
                  </button>
                  <Link
                    href="/alerts"
                    className="hidden h-8 items-center justify-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 text-sm font-medium text-slate-100 transition-all duration-200 hover:bg-white/8 sm:inline-flex"
                  >
                    <IconBell className="h-4 w-4" />
                    Alerts
                  </Link>
                  {actions}
                </div>
              </div>

              {showFirstRunTutorial ? <FirstRunTutorial /> : null}
              {showContextStrip ? (
                <div
                  aria-live="polite"
                  className="flex flex-wrap items-center gap-2 rounded-[24px] border border-white/8 bg-slate-950/60 p-3 text-xs text-slate-300"
                >
                  <StatusPill
                    label={mode === "live" ? "Live mode" : "Demo mode"}
                    detail={mode === "live" ? "provider checked, cached if needed" : "seeded, repeatable, no live calls"}
                    tone={mode === "live" ? "live" : "demo"}
                  />
                  <StatusPill label="Decision support" detail="no real-money execution" tone="safe" />
                  <StatusPill label="Paper trading only" detail="portfolio actions are simulated" tone="paper" />
                  <Link
                    href="/settings"
                    className="ml-auto inline-flex min-h-8 items-center rounded-full border border-white/10 bg-white/5 px-3 font-semibold text-slate-100 transition hover:bg-white/8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/60"
                  >
                    Check sources
                  </Link>
                </div>
              ) : null}
            </header>
            <div className="pt-5">{children}</div>
          </Card>
        </main>
      </div>
      {mobileMoreOpen ? (
        <div className="fixed inset-x-3 bottom-[calc(5.8rem_+_env(safe-area-inset-bottom))] z-40 rounded-[28px] border border-white/10 bg-slate-950/95 p-3 shadow-[0_24px_70px_rgba(0,0,0,0.55)] backdrop-blur-xl lg:hidden">
          <div className="mb-3 flex items-center justify-between gap-3 px-1">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">More tools</p>
            <button
              type="button"
              onClick={() => {
                setMobileMoreOpen(false);
                window.dispatchEvent(new Event("markets:open-command-palette"));
              }}
              className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1.5 text-xs font-semibold text-cyan-100"
            >
              Search
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {mobileMoreItems.map((item) => {
              const Icon = item.icon;
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-3 rounded-2xl border px-3 py-3 text-sm font-semibold transition",
                    active
                      ? "border-cyan-300/24 bg-cyan-300/12 text-cyan-100"
                      : "border-white/8 bg-white/4 text-slate-300 hover:bg-white/7 hover:text-white",
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      ) : null}
      <nav className="fixed inset-x-3 bottom-3 z-40 rounded-[28px] border border-white/10 bg-slate-950/92 p-2 shadow-[0_20px_60px_rgba(0,0,0,0.5)] backdrop-blur-xl lg:hidden">
        <div className="grid grid-cols-7 gap-1">
          {mobileNavItems.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex min-w-0 flex-col items-center justify-center gap-1 rounded-2xl px-1 py-2 text-[10px] font-semibold transition",
                  active ? "bg-cyan-300/12 text-cyan-100" : "text-slate-400 hover:bg-white/6 hover:text-slate-100",
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="truncate">{item.label}</span>
              </Link>
            );
          })}
          <button
            type="button"
            aria-expanded={mobileMoreOpen}
            aria-label="Open more navigation options"
            onClick={() => setMobileMoreOpen((value) => !value)}
            className={cn(
              "flex min-w-0 flex-col items-center justify-center gap-1 rounded-2xl px-1 py-2 text-[10px] font-semibold transition",
              mobileMoreOpen ? "bg-cyan-300/12 text-cyan-100" : "text-slate-400 hover:bg-white/6 hover:text-slate-100",
            )}
          >
            <IconShield className="h-4 w-4" />
            <span className="truncate">More</span>
          </button>
        </div>
      </nav>
    </div>
  );
}

function StatusPill({
  label,
  detail,
  tone,
}: {
  label: string;
  detail: string;
  tone: "live" | "demo" | "safe" | "paper";
}) {
  const styles = {
    live: "border-cyan-300/20 bg-cyan-300/10 text-cyan-100",
    demo: "border-amber-300/20 bg-amber-300/10 text-amber-100",
    safe: "border-emerald-300/20 bg-emerald-300/10 text-emerald-100",
    paper: "border-violet-300/20 bg-violet-300/10 text-violet-100",
  }[tone];

  return (
    <span className={cn("inline-flex min-h-8 items-center gap-2 rounded-full border px-3", styles)}>
      <span className="font-semibold">{label}</span>
      <span className="hidden text-slate-300/80 sm:inline">{detail}</span>
    </span>
  );
}
