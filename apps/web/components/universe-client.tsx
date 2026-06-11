"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fetchUniverse } from "@/lib/api";

const STORAGE_KEY = "markets-strategy-copilot:universe";

export function UniverseClient() {
  const [payload, setPayload] = useState<any>(null);
  const [selected, setSelected] = useState("All");
  const [query, setQuery] = useState("");

  useEffect(() => {
    setSelected(window.localStorage.getItem(STORAGE_KEY) || "All");
    fetchUniverse().then(setPayload);
  }, []);

  function choose(name: string) {
    window.localStorage.setItem(STORAGE_KEY, name);
    setSelected(name);
  }

  const symbols = useMemo(() => {
    if (!payload) return [];
    const group = payload.groups.find((item: any) => item.name === selected);
    const allowed = new Set(group?.symbols ?? payload.symbols.map((item: any) => item.symbol));
    const needle = query.toLowerCase().trim();
    return payload.symbols.filter((item: any) => allowed.has(item.symbol) && (!needle || `${item.symbol} ${item.name} ${item.assetClass}`.toLowerCase().includes(needle)));
  }, [payload, query, selected]);

  return (
    <AppFrame
      eyebrow="Watchlists"
      title="Universe Builder"
      subtitle="Choose a realistic cross-asset universe, persist it locally, and open any symbol directly into research mode."
    >
      {!payload ? (
        <Card className="p-8 text-sm text-slate-400">Loading tracked universe...</Card>
      ) : (
        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
              <div>
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Universe presets</p>
                <h2 className="mt-2 text-xl font-semibold text-white">{payload.total} local tracked instruments</h2>
                <p className="mt-2 text-sm text-slate-400">{payload.storagePolicy}</p>
              </div>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search symbols..."
                className="h-10 rounded-full border border-white/10 bg-slate-950 px-4 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-300/40"
              />
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {payload.groups.map((group: any) => (
                <Button key={group.name} size="sm" variant={selected === group.name ? "default" : "secondary"} onClick={() => choose(group.name)}>
                  {group.name} ({group.count})
                </Button>
              ))}
            </div>
          </Card>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {symbols.map((item: any) => (
              <Card key={item.symbol} className="p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-xl font-semibold text-white">{item.symbol}</h3>
                    <p className="mt-1 text-sm text-slate-400">{item.name}</p>
                  </div>
                  <Badge>{item.assetClass}</Badge>
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-500">{item.description}</p>
                <div className="mt-4 flex gap-2">
                  <Link href={`/asset/${item.symbol}`}><Button size="sm">Open detail</Button></Link>
                  <Link href={`/governance?symbol=${item.symbol}`}><Button size="sm" variant="secondary">Governance</Button></Link>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </AppFrame>
  );
}
