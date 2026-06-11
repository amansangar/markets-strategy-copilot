"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { fetchDataCoverage } from "@/lib/api";

export function CoverageClient() {
  const [payload, setPayload] = useState<any>(null);

  useEffect(() => {
    fetchDataCoverage().then(setPayload);
  }, []);

  return (
    <AppFrame
      eyebrow="Operations"
      title="Data Coverage"
      subtitle="Map which assets have enough local evidence for bars, news, filings, signals, backtests, and audit-ready outputs."
    >
      {!payload ? (
        <Card className="p-8 text-sm text-slate-400">Loading data coverage map...</Card>
      ) : (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <Metric label="Symbols" value={String(payload.summary.symbols)} />
            <Metric label="Average Coverage" value={`${Math.round(payload.summary.averageCoverage)}/100`} />
            <Metric label="Excellent" value={String(payload.summary.excellent)} />
            <Metric label="Watch / Thin" value={String(payload.summary.watchOrThin)} />
          </div>
          <Card className="overflow-hidden">
            <div className="border-b border-white/8 p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Coverage matrix</p>
              <p className="mt-2 text-sm text-slate-400">{payload.caveat}</p>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-white/8 bg-white/4 text-slate-400">
                  <tr>
                    {["Symbol", "Score", "1D Bars", "5m Bars", "News", "Filings", "Signals", "Backtests", "Status"].map((column) => <th key={column} className="px-4 py-3 font-medium">{column}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {payload.rows.map((row: any) => (
                    <tr key={row.symbol} className="border-b border-white/6 text-slate-200 last:border-b-0">
                      <td className="px-4 py-3"><Link href={`/asset/${row.symbol}`} className="text-cyan-200 hover:text-cyan-100">{row.symbol}</Link></td>
                      <td className="px-4 py-3">{row.coverageScore}</td>
                      <td className="px-4 py-3">{row.dailyBars}</td>
                      <td className="px-4 py-3">{row.intradayBars}</td>
                      <td className="px-4 py-3">{row.news}</td>
                      <td className="px-4 py-3">{row.filings}</td>
                      <td className="px-4 py-3">{row.signals}</td>
                      <td className="px-4 py-3">{row.backtests}</td>
                      <td className="px-4 py-3"><Badge>{row.status}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </AppFrame>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Card className="p-4">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-semibold text-white">{value}</p>
    </Card>
  );
}
