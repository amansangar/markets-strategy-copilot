"use client";

import { useCallback, useEffect, useState } from "react";

export type MarketMode = "demo" | "live";

const STORAGE_KEY = "markets-strategy-copilot:mode:v2";
const LEGACY_STORAGE_KEY = "markets-strategy-copilot:mode";

function readStoredMode(): MarketMode {
  if (typeof window === "undefined") return "demo";
  const stored = window.sessionStorage.getItem(STORAGE_KEY);
  if (stored === "demo" || stored === "live") {
    return stored;
  }
  return "demo";
}

export function useMarketMode(): [MarketMode, (mode: MarketMode, options?: { persist?: boolean }) => void] {
  const [mode, setModeState] = useState<MarketMode>("demo");

  useEffect(() => {
    window.localStorage.removeItem(LEGACY_STORAGE_KEY);
    window.sessionStorage.removeItem(LEGACY_STORAGE_KEY);
    setModeState(readStoredMode());
    function handleStorage(event: StorageEvent) {
      if (event.key === STORAGE_KEY) setModeState(readStoredMode());
    }
    function handleModeChange(event: Event) {
      const nextMode = (event as CustomEvent<{ mode?: MarketMode }>).detail?.mode;
      setModeState(nextMode === "demo" || nextMode === "live" ? nextMode : readStoredMode());
    }
    window.addEventListener("storage", handleStorage);
    window.addEventListener("markets-mode-change", handleModeChange);
    return () => {
      window.removeEventListener("storage", handleStorage);
      window.removeEventListener("markets-mode-change", handleModeChange);
    };
  }, []);

  const setMode = useCallback((nextMode: MarketMode, options?: { persist?: boolean }) => {
    if (options?.persist !== false) {
      window.sessionStorage.setItem(STORAGE_KEY, nextMode);
    }
    setModeState(nextMode);
    window.dispatchEvent(new CustomEvent("markets-mode-change", { detail: { mode: nextMode } }));
  }, []);

  return [mode, setMode];
}
