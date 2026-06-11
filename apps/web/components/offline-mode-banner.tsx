"use client";

import { useEffect, useState } from "react";

import { IconShield } from "@/components/icons";

export function OfflineModeBanner() {
  const [online, setOnline] = useState(true);

  useEffect(() => {
    setOnline(window.navigator.onLine);
    function update() {
      setOnline(window.navigator.onLine);
    }
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  if (online) {
    return null;
  }

  return (
    <div className="fixed left-1/2 top-3 z-50 flex -translate-x-1/2 items-center gap-2 rounded-full border border-amber-300/25 bg-slate-950/95 px-4 py-2 text-xs font-medium uppercase tracking-[0.18em] text-amber-100 shadow-2xl shadow-amber-950/30 backdrop-blur">
      <IconShield className="h-4 w-4" />
      Offline demo-safe mode active
    </div>
  );
}
