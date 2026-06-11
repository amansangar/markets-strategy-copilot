"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

const commands = [
  { label: "Dashboard", href: "/", tags: "home overview signals chart" },
  { label: "Ask AI", href: "/assistant", tags: "copilot explain signal risk news filings" },
  { label: "Asset Research", href: "/asset/SPY", tags: "symbol chart replay filings" },
  { label: "Find Setups", href: "/scanner", tags: "scanner filters discovery trade ideas" },
  { label: "Charts", href: "/terminal", tags: "multi chart drawings patterns comparison" },
  { label: "Backtest", href: "/strategy-tester", tags: "strategy tester walk-forward fees slippage" },
  { label: "Portfolio", href: "/portfolio", tags: "paper positions pnl exposure" },
  { label: "Alerts", href: "/alerts", tags: "price signal news provider alerts" },
  { label: "Investment Notes", href: "/reports", tags: "pdf report export" },
  { label: "Workspace", href: "/workspace", tags: "notes watchlists layouts" },
  { label: "Research Toolkit", href: "/pro-terminal", tags: "advanced labs tools terminal workflow" },
  { label: "Settings", href: "/settings", tags: "providers fallback health setup advanced" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((current) => !current);
      }
      if (event.key === "Escape") setOpen(false);
    }
    function onOpenRequest() {
      setOpen(true);
    }
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("markets:open-command-palette", onOpenRequest);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("markets:open-command-palette", onOpenRequest);
    };
  }, []);

  const filtered = useMemo(() => {
    const needle = query.toLowerCase().trim();
    if (!needle) return commands;
    return commands.filter((item) => `${item.label} ${item.tags}`.toLowerCase().includes(needle));
  }, [query]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/70 px-4 py-20 backdrop-blur" onClick={() => setOpen(false)}>
      <div className="mx-auto max-w-2xl rounded-[28px] border border-white/10 bg-slate-950/95 p-4 shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <input
          autoFocus
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search screens, symbols, reports, alerts..."
          className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500"
        />
        <div className="mt-3 space-y-2">
          {filtered.map((item) => (
            <Link key={item.href} href={item.href} onClick={() => setOpen(false)} className="block rounded-2xl border border-white/8 bg-white/4 px-4 py-3 transition hover:border-cyan-300/25 hover:bg-cyan-300/10">
              <p className="text-sm font-medium text-white">{item.label}</p>
              <p className="mt-1 text-xs text-slate-500">{item.href} • {item.tags}</p>
            </Link>
          ))}
        </div>
        <p className="mt-4 text-xs text-slate-500">Press Esc to close. Press Ctrl+K to reopen.</p>
      </div>
    </div>
  );
}
