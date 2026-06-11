"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { AppFrame } from "@/components/app-frame";
import { IconChart, IconShield, IconSignal } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { fetchWorkspace } from "@/lib/api";
import type { WorkspaceResponse } from "@/lib/types";

export function WorkspaceClient() {
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null);

  useEffect(() => {
    fetchWorkspace().then(setWorkspace);
  }, []);

  return (
    <AppFrame
      eyebrow="Workspace"
      title="Research Workspace"
      subtitle="Saved watchlists, scanner presets, chart layouts, symbol notes, and report history. Clerk is optional; guest/local mode remains available."
    >
      {!workspace ? (
        <Card className="p-8 text-sm text-slate-400">Loading workspace...</Card>
      ) : (
        <div className="space-y-4">
          <Card className="p-5">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <IconShield className="h-4 w-4 text-cyan-200" />
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Auth mode</p>
              </div>
              <Badge>{workspace.auth.mode.replaceAll("_", " ")}</Badge>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-300">{workspace.auth.detail}</p>
          </Card>

          <div className="grid gap-4 xl:grid-cols-2">
            <WorkspaceSection kind="watchlist" title="Saved watchlists" icon={<IconChart className="h-4 w-4 text-emerald-200" />} items={workspace.savedWatchlists} />
            <WorkspaceSection kind="scanner" title="Saved scanners" icon={<IconSignal className="h-4 w-4 text-cyan-200" />} items={workspace.savedScanners} />
            <WorkspaceSection kind="layout" title="Chart layouts" icon={<IconChart className="h-4 w-4 text-amber-200" />} items={workspace.chartLayouts} />
            <WorkspaceSection kind="note" title="Symbol notes" icon={<IconShield className="h-4 w-4 text-violet-200" />} items={workspace.symbolNotes} />
          </div>
        </div>
      )}
    </AppFrame>
  );
}

function WorkspaceSection({
  title,
  icon,
  items,
  kind,
}: {
  title: string;
  icon: ReactNode;
  items: Array<Record<string, unknown>>;
  kind: "watchlist" | "scanner" | "layout" | "note";
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center gap-2">
        {icon}
        <h2 className="text-lg font-semibold text-white">{title}</h2>
      </div>
      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <div key={String(item.id)} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
            <p className="text-sm font-medium text-white">{String(item.name)}</p>
            <WorkspacePayload kind={kind} payload={(item.payload ?? {}) as Record<string, unknown>} />
          </div>
        ))}
      </div>
    </Card>
  );
}

function WorkspacePayload({ kind, payload }: { kind: "watchlist" | "scanner" | "layout" | "note"; payload: Record<string, unknown> }) {
  if (kind === "watchlist") {
    const symbols = asStringArray(payload.symbols);
    return (
      <div className="mt-3">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Markets included</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {symbols.map((symbol) => <Badge key={symbol}>{symbol}</Badge>)}
        </div>
      </div>
    );
  }

  if (kind === "scanner") {
    return (
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        <ReadableStat label="Signal" value={String(payload.action ?? "Any")} />
        <ReadableStat label="Minimum confidence" value={formatConfidenceValue(payload.minConfidence)} />
        <ReadableStat label="Regime" value={String(payload.regime ?? "Any").replaceAll("_", " ")} />
      </div>
    );
  }

  if (kind === "layout") {
    const overlays = asStringArray(payload.overlays);
    const panes = asStringArray(payload.panes);
    return (
      <div className="mt-3 space-y-3">
        <ChipGroup label="Chart overlays" values={overlays} />
        <ChipGroup label="Lower panels" values={panes} />
      </div>
    );
  }

  return (
    <div className="mt-3 rounded-2xl border border-white/8 bg-slate-950/40 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge>{String(payload.symbol ?? "Note")}</Badge>
        <span className="text-xs uppercase tracking-[0.2em] text-slate-500">Research note</span>
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-300">{String(payload.note ?? "No note saved yet.")}</p>
    </div>
  );
}

function ChipGroup({ label, values }: { label: string; values: string[] }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {values.map((value) => <Badge key={value}>{value}</Badge>)}
      </div>
    </div>
  );
}

function ReadableStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-slate-950/40 p-3">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-white">{value}</p>
    </div>
  );
}

function asStringArray(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item)) : [];
}

function formatConfidenceValue(value: unknown) {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "Any";
}
