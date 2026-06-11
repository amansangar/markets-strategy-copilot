"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { IconGauge, IconShield, IconSignal } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const STORAGE_KEY = "markets-strategy-copilot:first-run-tutorial-dismissed";

export function FirstRunTutorial() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(window.localStorage.getItem(STORAGE_KEY) !== "true");
  }, []);

  if (!visible) {
    return null;
  }

  function dismiss() {
    window.localStorage.setItem(STORAGE_KEY, "true");
    setVisible(false);
  }

  return (
    <Card className="border-cyan-300/16 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.14),rgba(15,23,42,0.78)_44%,rgba(2,6,23,0.88))] p-3 sm:p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-cyan-100">First-time guide</p>
          <h2 className="mt-2 text-base font-semibold text-white sm:text-lg">Live-first, demo-safe research terminal</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300 max-sm:hidden">
            The app opens in Demo mode so the first run is safe, fast, and repeatable. Switch to Live when you want provider-backed data, and use Setup for a beginner walkthrough.
          </p>
          <p className="mt-1 text-sm leading-5 text-slate-300 sm:hidden">Use Setup for the walkthrough, or hide this guide when ready.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/setup">
            <Button size="sm" className="gap-2 rounded-full">
              <IconShield className="h-4 w-4" />
              Open setup
            </Button>
          </Link>
          <Link href="/quality">
            <Button variant="secondary" size="sm" className="gap-2 rounded-full">
              <IconSignal className="h-4 w-4" />
              Signal quality
            </Button>
          </Link>
          <Button variant="ghost" size="sm" className="gap-2 rounded-full" onClick={dismiss}>
            <IconGauge className="h-4 w-4" />
            Hide
          </Button>
        </div>
      </div>
    </Card>
  );
}
