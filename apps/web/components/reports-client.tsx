"use client";

import { useEffect, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { LiveFallbackNotice } from "@/components/live-fallback-notice";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { exportReport, fetchReports, reportDownloadUrl } from "@/lib/api";
import { DEMO_SYMBOLS, PRESETS } from "@/lib/constants";
import { formatDateTime } from "@/lib/format";
import { liveFallbackReasonFromError, shouldAttemptLiveFallback } from "@/lib/live-fallback";
import { useMarketMode } from "@/lib/use-market-mode";

export function ReportsClient() {
  const [mode] = useMarketMode();
  const [symbol, setSymbol] = useState<(typeof DEMO_SYMBOLS)[number]>("SPY");
  const [preset, setPreset] = useState<(typeof PRESETS)[number]>("Trend Following");
  const [reports, setReports] = useState<any[]>([]);
  const [latestReport, setLatestReport] = useState<any | null>(null);
  const [fallbackNotice, setFallbackNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [showAllReports, setShowAllReports] = useState(false);

  const visibleReports = showAllReports ? reports : reports.slice(0, 5);

  useEffect(() => {
    setMounted(true);
    fetchReports().then(setReports).catch((reason) => setError(reason instanceof Error ? reason.message : "Report history failed to load"));
  }, []);

  async function handleExport() {
    setError(null);
    setIsExporting(true);
    try {
      const report = await exportReport(symbol, mode, preset);
      setLatestReport(report);
      setReports((current) => [report, ...current]);
      triggerReportDownload(report);
    } catch (reason) {
      if (!shouldAttemptLiveFallback(mode)) {
        setError(reason instanceof Error ? reason.message : "Report export failed");
        return;
      }

      setFallbackNotice(liveFallbackReasonFromError(reason));
      try {
        const report = await exportReport(symbol, "demo", preset);
        setLatestReport(report);
        setReports((current) => [report, ...current]);
        triggerReportDownload(report);
      } catch (demoReason) {
        setError(demoReason instanceof Error ? demoReason.message : "Demo report export failed");
      }
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <AppFrame
      eyebrow="Investment Notes"
      title="Reports / Investment Notes"
      subtitle="Export concise professional notes with current rationale, cited news, TCA-aware metrics, and chart snapshots saved to the artefacts folder."
      actions={<Button onClick={handleExport} disabled={!mounted || isExporting}>{isExporting ? "Exporting..." : "Export PDF note"}</Button>}
    >
      <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <Card className="p-5">
          <div className="space-y-4">
            {fallbackNotice && <LiveFallbackNotice message={fallbackNotice} />}
            <Control label="Symbol">
              <NativeSelect value={symbol} onChange={(value) => setSymbol(value as (typeof DEMO_SYMBOLS)[number])}>
                {DEMO_SYMBOLS.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </NativeSelect>
            </Control>
            <Control label="Preset">
              <NativeSelect value={preset} onChange={(value) => setPreset(value as (typeof PRESETS)[number])}>
                {PRESETS.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </NativeSelect>
            </Control>
            <div className="rounded-[22px] border border-white/8 bg-white/4 p-4 text-sm text-slate-300">
              Generated PDFs are written to `artefacts/exports` and tracked by the backend metadata store for repeat viewing.
            </div>
            {latestReport && (
              <div className="rounded-[22px] border border-emerald-300/14 bg-emerald-300/8 p-4 text-sm text-slate-100">
                <p className="font-medium">Latest export ready</p>
                <p className="mt-1 text-slate-300">{displayReportFilename(latestReport.path)}</p>
                <a
                  className="mt-3 inline-flex rounded-full border border-emerald-200/25 bg-emerald-200/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-100 transition hover:bg-emerald-200/18"
                  href={reportDownloadUrl(latestReport)}
                  download={displayReportFilename(latestReport.path)}
                >
                  Download PDF
                </a>
              </div>
            )}
            {error && (
              <div className="rounded-[22px] border border-rose-300/14 bg-rose-300/8 p-4 text-sm text-rose-100">
                {error}
              </div>
            )}
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <h2 className="text-lg font-semibold text-white">Recent exports</h2>
              <p className="mt-1 text-sm text-slate-400">Showing clean filenames only. New exports use timestamped names.</p>
            </div>
            {reports.length > 5 ? (
              <Button type="button" variant="secondary" size="sm" onClick={() => setShowAllReports((value) => !value)}>
                {showAllReports ? "Show latest 5" : `View all ${reports.length}`}
              </Button>
            ) : null}
          </div>
          <div className="mt-4 space-y-3">
            {visibleReports.map((report) => (
              <div key={report.reportId} className="rounded-[22px] border border-white/8 bg-white/4 p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-white">{report.symbol}</p>
                  <span className="text-xs uppercase tracking-[0.22em] text-slate-500">{report.mode}</span>
                </div>
                <p className="mt-2 text-sm text-slate-300">{displayReportFilename(report.path)}</p>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                  <p className="text-xs text-slate-500">{formatDateTime(report.createdAt)}</p>
                  <a
                    className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold text-slate-100 transition hover:border-cyan-300/25 hover:bg-cyan-300/10"
                    href={reportDownloadUrl(report)}
                    download={displayReportFilename(report.path)}
                  >
                    Download PDF
                  </a>
                </div>
              </div>
            ))}
            {!reports.length ? (
              <div className="rounded-[22px] border border-white/8 bg-white/4 p-4 text-sm leading-6 text-slate-400">
                No reports exported yet. Choose a symbol and press Export PDF note to create the first investment note.
              </div>
            ) : null}
          </div>
        </Card>
      </div>
    </AppFrame>
  );
}

function displayReportFilename(pathValue: string | null | undefined) {
  if (!pathValue) {
    return "investment-note.pdf";
  }
  return pathValue.split(/[\\/]/).filter(Boolean).at(-1) ?? "investment-note.pdf";
}

function triggerReportDownload(report: { reportId: string; path?: string; downloadUrl?: string | null }) {
  const link = document.createElement("a");
  link.href = reportDownloadUrl(report);
  link.download = displayReportFilename(report.path);
  link.rel = "noreferrer";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function Control({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-2 text-xs uppercase tracking-[0.24em] text-slate-500">{label}</p>
      {children}
    </div>
  );
}
