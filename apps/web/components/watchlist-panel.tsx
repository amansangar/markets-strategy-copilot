"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { IconTrendDown, IconTrendUp } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { formatConfidence, formatPercent, formatPrice } from "@/lib/format";
import type { WatchlistRow } from "@/lib/types";
import { cn } from "@/lib/utils";

const UNIVERSE_STORAGE_KEY = "markets-strategy-copilot:universe";

export function WatchlistPanel({
  rows,
  selectedSymbol,
  onSelect,
}: {
  rows: WatchlistRow[];
  selectedSymbol: string;
  onSelect: (symbol: string) => void;
}) {
  const [universe, setUniverse] = useState("All");
  const [query, setQuery] = useState("");

  useEffect(() => {
    setUniverse(window.localStorage.getItem(UNIVERSE_STORAGE_KEY) || "All");
  }, []);

  function chooseUniverse(nextUniverse: string) {
    window.localStorage.setItem(UNIVERSE_STORAGE_KEY, nextUniverse);
    setUniverse(nextUniverse);
  }

  const universes = useMemo(() => {
    const classes = Array.from(new Set(rows.map((row) => row.assetClass))).sort();
    return ["All", ...classes.map((item) => item.charAt(0).toUpperCase() + item.slice(1))];
  }, [rows]);

  const filteredRows = useMemo(() => {
    const selectedClass = universe === "All" ? null : universe.toLowerCase();
    const needle = query.toLowerCase().trim();
    return rows.filter((row) => {
      const matchesUniverse = !selectedClass || row.assetClass.toLowerCase() === selectedClass;
      const matchesSearch = !needle || `${row.symbol} ${row.name} ${row.assetClass}`.toLowerCase().includes(needle);
      return matchesUniverse && matchesSearch;
    });
  }, [query, rows, universe]);

  return (
    <Card className="p-4 xl:sticky xl:top-4">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Markets to watch</p>
          <h2 className="mt-2 text-lg font-semibold text-white">Watchlist</h2>
          <p className="mt-1 text-xs text-cyan-100/80">Showing {selectedSymbol} on the chart</p>
        </div>
        <Badge>{filteredRows.length}/{rows.length} tracked</Badge>
      </div>

      <div className="mb-4 grid gap-2">
        <NativeSelect value={universe} onChange={chooseUniverse}>
          {universes.map((item) => <option key={item} value={item}>{item}</option>)}
        </NativeSelect>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search symbol or name..."
          className="h-10 rounded-full border border-white/10 bg-slate-950 px-4 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-300/40"
        />
      </div>

      <div className="max-h-[560px] space-y-3 overflow-y-auto pr-1 xl:max-h-[640px]">
        {filteredRows.map((row) => {
          const positive = row.changePct >= 0;
          const selected = row.symbol === selectedSymbol;
          return (
            <div
              key={row.symbol}
              className={cn(
                "w-full rounded-[22px] border p-4 text-left transition",
                selected
                  ? "border-cyan-200/40 bg-cyan-300/12 shadow-[0_0_0_1px_rgba(103,232,249,0.22),0_18px_32px_rgba(0,0,0,0.24)]"
                  : "border-white/8 bg-white/3 hover:bg-white/6",
              )}
            >
              <button
                type="button"
                onClick={() => onSelect(row.symbol)}
                className="w-full text-left"
                aria-pressed={selected}
                aria-label={`Select ${row.symbol} on dashboard chart`}
              >
                <div className="grid grid-cols-[minmax(0,1fr)_minmax(72px,auto)] items-start gap-3">
                  <div className="min-w-0">
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                      <h3 className="min-w-0 text-base font-semibold text-white">{row.symbol}</h3>
                      <span className="truncate text-xs uppercase tracking-[0.24em] text-slate-500">{row.assetClass}</span>
                      {selected ? <span className="shrink-0 rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-100">On chart</span> : null}
                    </div>
                    <p className="mt-1 truncate text-xs text-slate-500">{row.name}</p>
                  </div>
                  <div className="min-w-[72px] max-w-[96px] justify-self-end overflow-hidden text-right">
                    <p className="truncate text-base font-semibold text-white" title={formatPrice(row.lastPrice)}>{formatPrice(row.lastPrice)}</p>
                    <p className={cn("mt-1 inline-flex max-w-full items-center justify-end gap-1 truncate text-xs", positive ? "text-emerald-300" : "text-rose-300")} title={formatPercent(row.changePct)}>
                      {positive ? <IconTrendUp className="h-3.5 w-3.5" /> : <IconTrendDown className="h-3.5 w-3.5" />}
                      <span className="truncate">{formatPercent(row.changePct)}</span>
                    </p>
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-between gap-2 text-xs text-slate-400">
                  <span>{row.signal.replaceAll("_", " ")}</span>
                  <span>{formatConfidence(row.confidence)}</span>
                  <span>{row.regime.replaceAll("_", " ")}</span>
                </div>
              </button>
              <div className="mt-3 flex items-center justify-between gap-3 text-xs text-slate-500">
                <span>News mood {row.sentiment > 0.1 ? "positive" : row.sentiment < -0.1 ? "negative" : "neutral"}</span>
                <Link href={`/asset/${row.symbol}`} className="text-cyan-200 hover:text-cyan-100">
                  Research
                </Link>
              </div>
            </div>
          );
        })}
        {!filteredRows.length && (
          <div className="rounded-[22px] border border-white/8 bg-white/4 p-4 text-sm leading-6 text-slate-400">
            No markets match that filter. Choose All or clear the search box.
          </div>
        )}
      </div>
    </Card>
  );
}
