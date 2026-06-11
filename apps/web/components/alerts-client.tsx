"use client";

import { useEffect, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { fetchAlertCenter, fetchAlerts, toggleAlert } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

export function AlertsClient() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [center, setCenter] = useState<any>(null);

  useEffect(() => {
    fetchAlerts().then(setAlerts);
    fetchAlertCenter().then(setCenter);
  }, []);

  async function handleToggle(alertId: string) {
    const updated = await toggleAlert(alertId);
    setAlerts((current) => current.map((alert) => (alert.id === alertId ? updated : alert)));
  }

  return (
    <AppFrame
      eyebrow="Explainable Monitoring"
      title="Alerts"
      subtitle="Track rule-based price, indicator, and signal conditions with transparent trigger logic and an audit-friendly history."
    >
      <div className="space-y-4">
        {center && (
          <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Alert center</p>
              <h2 className="mt-2 text-2xl font-semibold text-white">
                {center.summary.enabledAlerts} of {center.summary.totalAlerts} enabled
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-400">{center.summary.cooldownPolicy}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {center.supportedAlertTypes.map((kind: string) => (
                  <Badge key={kind}>{kind.replaceAll("_", " ")}</Badge>
                ))}
              </div>
            </Card>
            <Card className="p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Delivery channels</p>
              <div className="mt-4 space-y-3">
                {center.channels.map((channel: any) => (
                  <div key={channel.name} className="rounded-[20px] border border-white/8 bg-white/4 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-white">{channel.name}</p>
                      <Badge>{channel.enabled ? "enabled" : "disabled"}</Badge>
                    </div>
                    <p className="mt-2 text-sm text-slate-400">{channel.detail}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-2">
          {alerts.map((alert) => (
            <Card key={alert.id} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{alert.kind}</p>
                  <h2 className="mt-2 text-xl font-semibold text-white">{alert.name}</h2>
                  <p className="mt-2 text-sm text-slate-400">{alert.symbol}</p>
                </div>
                <Switch checked={alert.enabled} label={`Toggle ${alert.name}`} onCheckedChange={() => handleToggle(alert.id)} />
              </div>
              <div className="mt-5 rounded-[22px] border border-white/8 bg-white/4 p-4">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Trigger</p>
                <p className="mt-2 text-sm leading-6 text-slate-200">{formatAlertRule(alert)}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {alertRuleChips(alert).map((chip) => (
                    <Badge key={chip}>{chip}</Badge>
                  ))}
                </div>
              </div>
              <div className="mt-4 rounded-[22px] border border-white/8 bg-white/4 p-4 text-sm text-slate-400">
                Browser notifications are the default path. Email delivery is enabled only when Resend credentials and sender are configured.
              </div>
              <Button variant="secondary" size="sm" className="mt-4 w-full" onClick={() => handleToggle(alert.id)}>
                {alert.enabled ? "Disable alert" : "Enable alert"}
              </Button>
            </Card>
          ))}
        </div>

        {center && (
          <Card className="p-5">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Delivery log</p>
            <div className="mt-4 space-y-3">
              {center.deliveryLog.map((item: any) => (
                <div key={item.id} className="rounded-[20px] border border-white/8 bg-white/4 p-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium text-white">{item.channel} • {item.status}</p>
                    <span className="text-xs text-slate-500">{formatDateTime(item.createdAt)}</span>
                  </div>
                  <p className="mt-2 text-slate-400">{item.detail}</p>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </AppFrame>
  );
}

function formatAlertRule(alert: any) {
  const rule = alert.rule ?? {};
  const symbol = alert.symbol ?? "this market";
  if (rule.type === "signal") {
    const preset = rule.preset ? ` using ${rule.preset}` : "";
    const confidence = typeof rule.minConfidence === "number" ? ` with at least ${Math.round(rule.minConfidence * 100)}% confidence` : "";
    return `Notify me when ${symbol} produces a signal${preset}${confidence}.`;
  }
  if (rule.type === "price_breakout") {
    const level = String(rule.level ?? "the watched level").replaceAll("_", " ");
    return `Notify me when ${symbol} breaks through ${level}.`;
  }
  if (rule.type === "macro_regime") {
    return "Notify me when the macro regime changes enough to affect risk appetite.";
  }
  if (rule.type === "provider_outage") {
    return "Notify me when an important data provider becomes unavailable or stale.";
  }
  return `Notify me when the saved ${String(alert.kind ?? "alert")} condition is met.`;
}

function alertRuleChips(alert: any) {
  const rule = alert.rule ?? {};
  const chips = [String(alert.kind ?? "alert").replaceAll("_", " ")];
  if (rule.preset) chips.push(String(rule.preset));
  if (typeof rule.minConfidence === "number") chips.push(`confidence >= ${Math.round(rule.minConfidence * 100)}%`);
  if (rule.level) chips.push(String(rule.level).replaceAll("_", " "));
  return chips;
}
