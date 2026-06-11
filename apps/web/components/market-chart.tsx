"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Card } from "@/components/ui/card";
import type { DashboardResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

declare global {
  interface Window {
    LightweightCharts?: any;
  }
}

type ChartPayload = DashboardResponse["chart"];
type SignalPayload = DashboardResponse["signal"];
type ChartRange = "1D" | "1M" | "3M" | "6M" | "ALL";

const overlayPalette: Record<string, string> = {
  ema21: "#1ec8ff",
  ema50: "#ffb45c",
  vwap: "#7cf3d0",
  bbUpper: "#5e74ff",
  bbLower: "#5e74ff",
};

const overlayLabels: Record<string, string> = {
  ema21: "EMA 21",
  ema50: "EMA 50",
  vwap: "VWAP",
  bbUpper: "Bollinger high",
  bbLower: "Bollinger low",
};

function toEpoch(value: string) {
  const timestamp = new Date(value).getTime();
  return Number.isFinite(timestamp) ? Math.floor(timestamp / 1000) : 0;
}

function chartTimeToEpoch(value: unknown) {
  if (typeof value === "number") {
    return value;
  }
  if (typeof value === "string") {
    return toEpoch(value);
  }
  if (value && typeof value === "object" && "year" in value && "month" in value && "day" in value) {
    const date = value as { year: number; month: number; day: number };
    return Math.floor(Date.UTC(date.year, date.month - 1, date.day) / 1000);
  }
  return null;
}

function formatChartTime(value: unknown, intraday: boolean) {
  const epoch = chartTimeToEpoch(value);
  if (!epoch) {
    return "";
  }
  const date = new Date(epoch * 1000);
  return intraday
    ? date.toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "2-digit" });
}

function toSeriesTime(value: string, intraday: boolean) {
  return intraday ? toEpoch(value) : value.slice(0, 10);
}

function syncRange(source: any, targets: any[]) {
  source.timeScale().subscribeVisibleTimeRangeChange((range: any) => {
    targets.forEach((chart) => {
      if (range) {
        chart.timeScale().setVisibleRange(range);
      }
    });
  });
}

function finitePoint(item: { time: string; value?: number | null }) {
  return isValidChartTime(item.time) && typeof item.value === "number" && Number.isFinite(item.value);
}

function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isValidChartTime(value: string) {
  return Boolean(value) && Number.isFinite(new Date(value).getTime());
}

function hasIntradayPrecision(value: string) {
  return value.includes("T") || /\d{1,2}:\d{2}/.test(value);
}

function finiteCandle(candle: ChartPayload["candles"][number]) {
  return (
    isValidChartTime(candle.time) &&
    finiteNumber(candle.open) &&
    finiteNumber(candle.high) &&
    finiteNumber(candle.low) &&
    finiteNumber(candle.close) &&
    finiteNumber(candle.volume)
  );
}

function dedupeByEpoch<T extends { time: string }>(items: T[]) {
  const byTime = new Map<number, T>();
  items.forEach((item) => {
    const epoch = toEpoch(item.time);
    if (epoch > 0) {
      byTime.set(epoch, item);
    }
  });
  return Array.from(byTime.entries())
    .sort(([left], [right]) => left - right)
    .map(([, item]) => item);
}

export function MarketChart({ chart, signal, hero = false }: { chart: ChartPayload; signal?: SignalPayload; hero?: boolean }) {
  const mainRef = useRef<HTMLDivElement | null>(null);
  const rsiRef = useRef<HTMLDivElement | null>(null);
  const macdRef = useRef<HTMLDivElement | null>(null);
  const [range, setRange] = useState<ChartRange>("1D");
  const [focusMode, setFocusMode] = useState(false);
  const [chartLibraryReady, setChartLibraryReady] = useState(false);
  const [crosshairInfo, setCrosshairInfo] = useState<string>("Move crosshair over chart for OHLC readout");
  const [activeOverlays, setActiveOverlays] = useState<Record<string, boolean>>({
    ema21: true,
    ema50: true,
    vwap: true,
    bbUpper: true,
    bbLower: true,
  });

  const rangeOptions = useMemo<ChartRange[]>(() => (chart.history ? ["1D", "1M", "3M", "6M", "ALL"] : ["1M", "3M", "6M", "ALL"]), [chart.history]);

  useEffect(() => {
    if (!chart.history && range === "1D") {
      setRange("6M");
    }
  }, [chart.history, range]);

  useEffect(() => {
    setCrosshairInfo("Move crosshair over chart for OHLC readout");
  }, [chart.symbol]);

  const displayChart = useMemo(() => {
    const sourceChart = chart.history && range !== "1D" ? chart.history : chart;
    const sourceCandles = dedupeByEpoch(sourceChart.candles.filter(finiteCandle));
    const rangeDays: Record<ChartRange, number | null> = {
      "1D": 1.35,
      "1M": 31,
      "3M": 93,
      "6M": 186,
      "ALL": null,
    };
    const fallbackBars: Record<ChartRange, number> = {
      "1D": 160,
      "1M": 35,
      "3M": 100,
      "6M": 190,
      "ALL": sourceCandles.length,
    };
    const latestTime = sourceCandles.at(-1)?.time;
    const cutoff =
      latestTime && rangeDays[range] !== null
        ? new Date(latestTime).getTime() - Number(rangeDays[range]) * 24 * 60 * 60 * 1000
        : null;
    let candles = cutoff
      ? sourceCandles.filter((item) => new Date(item.time).getTime() >= cutoff)
      : sourceCandles;
    if (candles.length < 10 && sourceCandles.length > candles.length) {
      candles = sourceCandles.slice(-fallbackBars[range]);
    }
    const allowedTimes = new Set(candles.map((item) => toEpoch(item.time)));
    const keepAllowedTime = (time: string) => allowedTimes.has(toEpoch(time)) && isValidChartTime(time);
    return {
      ...sourceChart,
      candles,
      overlays: Object.fromEntries(Object.entries(sourceChart.overlays).map(([key, values]) => [key, dedupeByEpoch(values.filter((item) => keepAllowedTime(item.time)))])),
      oscillators: Object.fromEntries(Object.entries(sourceChart.oscillators).map(([key, values]) => [key, dedupeByEpoch(values.filter((item) => keepAllowedTime(item.time)))])),
      markers: dedupeByEpoch(sourceChart.markers.filter((item) => keepAllowedTime(item.time))),
    };
  }, [chart, range]);

  const toggles = useMemo(() => Object.keys(displayChart.overlays), [displayChart.overlays]);

  useEffect(() => {
    if (window.LightweightCharts) {
      setChartLibraryReady(true);
      return;
    }

    const existingScript = document.querySelector<HTMLScriptElement>('script[data-lightweight-charts="true"]');
    const handleLoad = () => setChartLibraryReady(true);
    const handleError = () => setCrosshairInfo("Chart library failed to load");

    if (existingScript) {
      existingScript.addEventListener("load", handleLoad, { once: true });
      existingScript.addEventListener("error", handleError, { once: true });
      return () => {
        existingScript.removeEventListener("load", handleLoad);
        existingScript.removeEventListener("error", handleError);
      };
    }

    const script = document.createElement("script");
    script.src = "/vendor/lightweight-charts.standalone.production.js";
    script.async = true;
    script.dataset.lightweightCharts = "true";
    script.addEventListener("load", handleLoad, { once: true });
    script.addEventListener("error", handleError, { once: true });
    document.head.appendChild(script);
    return () => {
      script.removeEventListener("load", handleLoad);
      script.removeEventListener("error", handleError);
    };
  }, []);

  useEffect(() => {
    if (!chartLibraryReady || !mainRef.current || !rsiRef.current || !macdRef.current) {
      return;
    }

    const dateBucketCount = new Set(displayChart.candles.map((candle) => candle.time.slice(0, 10))).size;
    const isIntradayView = displayChart.candles.some((candle) => hasIntradayPrecision(candle.time)) && dateBucketCount < displayChart.candles.length;
    const candleLookup = new Map(
      displayChart.candles.map((candle) => [
        chartTimeToEpoch(toSeriesTime(candle.time, isIntradayView)),
        candle,
      ]),
    );
    const commonOptions = {
      layout: {
        background: { color: "transparent" },
        textColor: "#93a7c3",
        fontFamily: "var(--font-heading)",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.05)" },
        horzLines: { color: "rgba(255,255,255,0.05)" },
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.08)",
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.08)",
        timeVisible: isIntradayView,
        secondsVisible: false,
        tickMarkFormatter: (time: unknown) => formatChartTime(time, isIntradayView),
      },
      localization: {
        timeFormatter: (time: unknown) => formatChartTime(time, isIntradayView),
      },
      crosshair: {
        vertLine: { color: "rgba(94, 200, 255, 0.35)" },
        horzLine: { color: "rgba(94, 200, 255, 0.35)" },
      },
    } as const;

    const LightweightCharts = window.LightweightCharts;
    if (!LightweightCharts) {
      return;
    }
    const { createChart, CandlestickSeries, LineSeries, HistogramSeries, createSeriesMarkers } = LightweightCharts;

    const standardHeight = hero ? 480 : 360;
    const focusedHeight = hero ? 640 : 500;
    const mainWidth = Math.max(mainRef.current.clientWidth, 320);
    const rsiWidth = Math.max(rsiRef.current.clientWidth, 240);
    const macdWidth = Math.max(macdRef.current.clientWidth, 240);
    const mainChart = createChart(mainRef.current, { ...commonOptions, height: focusMode ? focusedHeight : standardHeight, width: mainWidth });
    const rsiChart = createChart(rsiRef.current, { ...commonOptions, height: 120, width: rsiWidth });
    const macdChart = createChart(macdRef.current, { ...commonOptions, height: 140, width: macdWidth });

    const candleSeries = mainChart.addSeries(CandlestickSeries, {
      upColor: "#11d896",
      downColor: "#ff6f91",
      borderVisible: false,
      wickUpColor: "#11d896",
      wickDownColor: "#ff6f91",
    });
    candleSeries.setData(
      displayChart.candles.map((candle) => ({
        time: toSeriesTime(candle.time, isIntradayView),
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      })),
    );
    const latestCandle = displayChart.candles.at(-1);
    const liveSignalMarker =
      latestCandle && signal
        ? [
            {
              time: toSeriesTime(latestCandle.time, isIntradayView),
              position: signal.action.includes("BUY") ? "belowBar" : signal.action.includes("SELL") ? "aboveBar" : "inBar",
              color: signal.action.includes("BUY") ? "#11d896" : signal.action.includes("SELL") ? "#ff6f91" : "#f3ca6f",
              shape: signal.action.includes("BUY") ? "arrowUp" : signal.action.includes("SELL") ? "arrowDown" : "circle",
              text: signal.action.replaceAll("_", " "),
            },
          ]
        : [];

    createSeriesMarkers(
      candleSeries,
      [
        ...displayChart.markers.map((marker) => ({
          time: toSeriesTime(marker.time, isIntradayView),
          position: marker.position,
          color: marker.color,
          shape: marker.shape,
          text: marker.text,
        })),
        ...liveSignalMarker,
      ],
    );

    if (signal && displayChart.candles.length) {
      const recentCandles = displayChart.candles.slice(-40);
      const support = Math.min(...recentCandles.map((candle) => candle.low));
      const resistance = Math.max(...recentCandles.map((candle) => candle.high));
      const priceLines: Array<{ price: number; color: string; title: string } | null> = [
        { price: signal.currentPrice, color: "#1ec8ff", title: "Current" },
        signal.stopLoss ? { price: signal.stopLoss, color: "#ff6f91", title: "Stop" } : null,
        signal.takeProfitLow ? { price: signal.takeProfitLow, color: "#11d896", title: "Target 1" } : null,
        signal.takeProfitHigh ? { price: signal.takeProfitHigh, color: "#47f6a1", title: "Target 2" } : null,
        { price: support, color: "#f3ca6f", title: "Support" },
        { price: resistance, color: "#f3ca6f", title: "Resistance" },
      ];

      priceLines
        .filter((line): line is { price: number; color: string; title: string } => line !== null && Number.isFinite(line.price))
        .forEach((line) => {
          if (typeof candleSeries.createPriceLine === "function") {
            candleSeries.createPriceLine({
              price: line.price,
              color: line.color,
              lineWidth: 1,
              lineStyle: 2,
              axisLabelVisible: true,
              title: line.title,
            });
          }
        });
    }

    const volumeSeries = mainChart.addSeries(HistogramSeries, {
      priceScaleId: "",
      color: "rgba(30, 200, 255, 0.35)",
      priceFormat: { type: "volume" },
      lastValueVisible: false,
    });
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.75, bottom: 0 } });
    volumeSeries.setData(
      displayChart.candles.map((candle) => ({
        time: toSeriesTime(candle.time, isIntradayView),
        value: candle.volume,
        color: candle.close >= candle.open ? "rgba(17, 216, 150, 0.35)" : "rgba(255, 111, 145, 0.35)",
      })),
    );

    const overlaySeries: any[] = [];
    toggles.forEach((overlayKey) => {
      const series = mainChart.addSeries(LineSeries, {
        color: overlayPalette[overlayKey] ?? "#cbd5ff",
        lineWidth: overlayKey.startsWith("bb") ? 1 : 2,
        lineStyle: overlayKey.startsWith("bb") ? 2 : 0,
        visible: activeOverlays[overlayKey],
        lastValueVisible: false,
      });
      series.setData(
        displayChart.overlays[overlayKey].filter(finitePoint).map((item) => ({
          time: toSeriesTime(item.time, isIntradayView),
          value: item.value as number,
        })),
      );
      overlaySeries.push(series);
    });

    const rsiSeries = rsiChart.addSeries(LineSeries, {
      color: "#f3ca6f",
      lineWidth: 2,
      lastValueVisible: false,
    });
    rsiSeries.setData(
      displayChart.oscillators.rsi.filter(finitePoint).map((item) => ({
        time: toSeriesTime(item.time, isIntradayView),
        value: item.value as number,
      })),
    );

    const macdSeries = macdChart.addSeries(LineSeries, {
      color: "#52b0ff",
      lineWidth: 2,
      lastValueVisible: false,
    });
    const macdSignalSeries = macdChart.addSeries(LineSeries, {
      color: "#ff9f62",
      lineWidth: 2,
      lastValueVisible: false,
    });
    macdSeries.setData(
      displayChart.oscillators.macd.filter(finitePoint).map((item) => ({
        time: toSeriesTime(item.time, isIntradayView),
        value: item.value as number,
      })),
    );
    macdSignalSeries.setData(
      displayChart.oscillators.macd.filter((item) => isValidChartTime(item.time) && finiteNumber(item.signal)).map((item) => ({
        time: toSeriesTime(item.time, isIntradayView),
        value: item.signal as number,
      })),
    );

    syncRange(mainChart, [rsiChart, macdChart]);
    const handleCrosshairMove = (param: any) => {
      const seriesPoint = param?.seriesData?.get?.(candleSeries);
      const time = param?.time;
      if (!time) {
        setCrosshairInfo("Move crosshair over chart for OHLC readout");
        return;
      }
      const fallbackCandle = candleLookup.get(chartTimeToEpoch(time));
      const candlePoint = seriesPoint ?? fallbackCandle;
      if (!candlePoint) {
        setCrosshairInfo("Move crosshair over chart for OHLC readout");
        return;
      }
      const volumePoint = param?.seriesData?.get?.(volumeSeries);
      const formattedTime = formatChartTime(time, isIntradayView);
      const volumeText =
        typeof volumePoint?.value === "number"
          ? `  Vol ${Math.round(volumePoint.value).toLocaleString("en-GB")}`
          : "";
      setCrosshairInfo(
        `${formattedTime}  O ${candlePoint.open.toFixed(2)}  H ${candlePoint.high.toFixed(2)}  L ${candlePoint.low.toFixed(2)}  C ${candlePoint.close.toFixed(2)}${volumeText}`,
      );
    };
    mainChart.subscribeCrosshairMove(handleCrosshairMove);
    rsiChart.subscribeCrosshairMove(handleCrosshairMove);
    macdChart.subscribeCrosshairMove(handleCrosshairMove);
    mainChart.timeScale().fitContent();
    rsiChart.timeScale().fitContent();
    macdChart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver(() => {
      mainChart.applyOptions({ width: Math.max(mainRef.current?.clientWidth ?? 0, 320) });
      rsiChart.applyOptions({ width: Math.max(rsiRef.current?.clientWidth ?? 0, 240) });
      macdChart.applyOptions({ width: Math.max(macdRef.current?.clientWidth ?? 0, 240) });
    });
    resizeObserver.observe(mainRef.current);
    resizeObserver.observe(rsiRef.current);
    resizeObserver.observe(macdRef.current);

    return () => {
      resizeObserver.disconnect();
      overlaySeries.forEach((series) => series);
      mainChart.remove();
      rsiChart.remove();
      macdChart.remove();
    };
  }, [activeOverlays, chartLibraryReady, displayChart, focusMode, hero, range, signal, toggles]);

  return (
    <Card className="min-w-0 max-w-full overflow-hidden p-4">
      <div className="flex min-w-0 flex-col items-start gap-3 border-b border-white/8 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Price chart</p>
          <h2 className="mt-2 text-xl font-semibold text-white">{chart.symbol}</h2>
          <p className="mt-1 font-mono text-xs text-cyan-100/80">{crosshairInfo.replace("Move crosshair over chart for OHLC readout", "Move over the chart to see price details")}</p>
          {signal ? (
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="rounded-full border border-cyan-300/18 bg-cyan-300/10 px-3 py-1 font-semibold text-cyan-100">
                Signal: {signal.action.replaceAll("_", " ")}
              </span>
              <span className="rounded-full border border-white/8 bg-white/5 px-3 py-1 text-slate-300">
                Confidence {Math.round(signal.confidence * 100)}%
              </span>
              {signal.stopLoss ? (
                <span className="rounded-full border border-rose-300/18 bg-rose-300/10 px-3 py-1 text-rose-100">
                  Stop {signal.stopLoss.toFixed(2)}
                </span>
              ) : null}
              {signal.takeProfitLow ? (
                <span className="rounded-full border border-emerald-300/18 bg-emerald-300/10 px-3 py-1 text-emerald-100">
                  Target {signal.takeProfitLow.toFixed(2)}
                  {signal.takeProfitHigh ? `-${signal.takeProfitHigh.toFixed(2)}` : ""}
                </span>
              ) : null}
            </div>
          ) : null}
        </div>
        <div className="flex w-full min-w-0 flex-wrap gap-2 sm:w-auto sm:justify-end">
          {rangeOptions.map((item) => (
            <button
              key={item}
              onClick={() => setRange(item)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-xs uppercase tracking-[0.18em] transition",
                range === item ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100" : "border-white/8 bg-white/4 text-slate-400",
              )}
            >
              {item}
            </button>
          ))}
          <button
            onClick={() => setFocusMode((current) => !current)}
            className={cn(
              "rounded-full border px-3 py-1.5 text-xs uppercase tracking-[0.18em] transition",
              focusMode ? "border-amber-300/20 bg-amber-300/10 text-amber-100" : "border-white/8 bg-white/4 text-slate-400",
            )}
          >
            {focusMode ? "Compact chart" : "Expand chart"}
          </button>
          {toggles.map((toggle) => (
            <button
              key={toggle}
              onClick={() => setActiveOverlays((current) => ({ ...current, [toggle]: !current[toggle] }))}
              className={cn(
                "rounded-full border px-3 py-1.5 text-xs uppercase tracking-[0.18em] transition",
                activeOverlays[toggle]
                  ? "border-cyan-300/20 bg-cyan-300/10 text-cyan-100"
                  : "border-white/8 bg-white/4 text-slate-400",
              )}
            >
              {overlayLabels[toggle] ?? toggle}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 space-y-3">
        <div
          ref={mainRef}
          className={cn(
            "min-w-0 max-w-full overflow-hidden",
            hero
              ? focusMode
                ? "h-[520px] md:h-[640px]"
                : "h-[360px] md:h-[480px]"
              : focusMode
                ? "h-[430px] md:h-[500px]"
                : "h-[320px] md:h-[360px]",
          )}
        />
        <div className="grid min-w-0 gap-3 xl:grid-cols-[1fr_1fr]">
          <div className="min-w-0 overflow-hidden rounded-[22px] border border-white/8 bg-white/[0.03] p-2">
            <p className="px-2 py-1 text-xs uppercase tracking-[0.22em] text-slate-500">RSI</p>
            <div ref={rsiRef} className="h-[120px] min-w-0 max-w-full overflow-hidden" />
          </div>
          <div className="min-w-0 overflow-hidden rounded-[22px] border border-white/8 bg-white/[0.03] p-2">
            <p className="px-2 py-1 text-xs uppercase tracking-[0.22em] text-slate-500">MACD</p>
            <div ref={macdRef} className="h-[140px] min-w-0 max-w-full overflow-hidden" />
          </div>
        </div>
      </div>

      <p className="mt-4 text-xs text-slate-500">
        {chart.attribution} •{" "}
        <a href={chart.attributionUrl} target="_blank" rel="noreferrer" className="text-cyan-200 hover:text-cyan-100">
          attribution link
        </a>
      </p>
    </Card>
  );
}
