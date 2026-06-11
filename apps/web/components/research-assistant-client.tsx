"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppFrame } from "@/components/app-frame";
import { IconChart, IconShield, IconSignal, IconTrendUp, IconWarning } from "@/components/icons";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { NativeSelect } from "@/components/ui/native-select";
import { askResearchAssistant } from "@/lib/api";
import { DEMO_SYMBOLS } from "@/lib/constants";
import { useMarketMode } from "@/lib/use-market-mode";

const starterQuestions = [
  "Explain the current signal in simple language.",
  "What would make this setup stronger or weaker?",
  "Which risk flags matter most before taking a paper trade?",
  "Summarise this asset for a quick investment note.",
];

const quickPrompts = [
  {
    title: "Signal check",
    body: "Plain-English BUY / SELL explanation with confidence and blockers.",
    question: "Explain the current signal in simple language.",
    icon: IconSignal,
  },
  {
    title: "Trade plan",
    body: "Stop, target zone, sizing caution, and what would invalidate the idea.",
    question: "Turn the current signal into a cautious paper-trade plan.",
    icon: IconTrendUp,
  },
  {
    title: "Risk review",
    body: "List the biggest things that could make this signal unreliable.",
    question: "Which risk flags matter most before taking a paper trade?",
    icon: IconShield,
  },
  {
    title: "Report wording",
    body: "Professional summary that avoids overclaiming performance.",
    question: "Summarise this asset for a quick investment note.",
    icon: IconChart,
  },
];

export function ResearchAssistantClient() {
  const [mode, setMode] = useMarketMode();
  const [symbol, setSymbol] = useState("SPY");
  const [question, setQuestion] = useState(starterQuestions[0]);
  const [response, setResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const candidate = new URLSearchParams(window.location.search).get("symbol");
    if (candidate) {
      setSymbol(candidate.toUpperCase());
    }
  }, []);

  async function ask() {
    setLoading(true);
    try {
      setResponse(await askResearchAssistant({ question, symbol, mode }));
    } catch (error) {
      setResponse({
        symbol,
        source: "local_timeout_fallback",
        provenance: { usesOpenAI: false },
        answer:
          "The AI layer did not respond quickly enough, so the app stayed usable in technical-only mode. Check the signal card, chart levels, risk flags, and news/filing tabs before making any paper-trade decision. This fallback is deliberate: the app should never pretend an unavailable AI answer is a real insight.",
        citations: [
          "Local fallback: OpenAI/API response exceeded the safe UI wait time.",
          "Decision support only: use chart, signal reasons, risk flags, and audit evidence before acting.",
          error instanceof Error ? error.message : "Assistant request did not complete.",
        ],
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppFrame
      eyebrow="AI Copilot"
      title="Ask for a market brief"
      subtitle="Ask simple questions about signals, risk, news, filings, and paper-trade planning. The AI explains evidence; it does not predict prices or place trades."
      actions={
        <div className="flex flex-wrap gap-2">
          <div className="w-32"><NativeSelect value={symbol} onChange={setSymbol}>{DEMO_SYMBOLS.map((item) => <option key={item} value={item}>{item}</option>)}</NativeSelect></div>
          <Button variant={mode === "demo" ? "default" : "secondary"} size="sm" onClick={() => setMode("demo")}>Demo</Button>
          <Button variant={mode === "live" ? "default" : "secondary"} size="sm" onClick={() => setMode("live")}>Live</Button>
        </div>
      }
    >
      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <Card className="p-4 md:p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Ask about {symbol}</p>
              <h2 className="mt-2 text-xl font-semibold text-white">What do you want to understand?</h2>
            </div>
            <Link href={`/asset/${symbol}`}>
              <Button size="sm" variant="secondary">Open chart</Button>
            </Link>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {quickPrompts.map((item) => {
              const Icon = item.icon;
              const active = question === item.question;
              return (
                <button
                  key={item.title}
                  type="button"
                  onClick={() => setQuestion(item.question)}
                  className={`rounded-[22px] border p-4 text-left transition ${
                    active ? "border-cyan-300/24 bg-cyan-300/10" : "border-white/8 bg-white/4 hover:border-cyan-300/18 hover:bg-white/6"
                  }`}
                >
                  <div className="flex items-center gap-2 text-sm font-semibold text-white">
                    <Icon className="h-4 w-4 text-cyan-100" />
                    {item.title}
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-400">{item.body}</p>
                </button>
              );
            })}
          </div>

          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            className="mt-4 min-h-28 w-full rounded-[24px] border border-white/10 bg-slate-950 p-4 text-sm leading-6 text-white outline-none placeholder:text-slate-500 focus:border-cyan-300/40"
                    placeholder="Example: Explain why SPY is a BUY or SELL right now and what would change it."
          />
          <div className="mt-4 flex flex-wrap gap-2">
            {starterQuestions.map((item) => <Button key={item} size="sm" variant="secondary" onClick={() => setQuestion(item)}>{item}</Button>)}
          </div>
          <Button className="mt-5 w-full" onClick={ask} disabled={loading || !question.trim()}>
            {loading ? "Thinking for a moment..." : "Ask AI Copilot"}
          </Button>
          <p className="mt-3 text-xs leading-5 text-slate-500">
            If AI is unavailable or slow, this page falls back to deterministic technical guidance instead of hanging.
          </p>
        </Card>

        <Card className="min-h-[420px] p-4 md:p-5">
          {!response ? (
            <div className="grid h-full gap-4 lg:grid-cols-[1fr_0.9fr]">
              <div className="rounded-[26px] border border-cyan-300/14 bg-cyan-300/7 p-5">
                <Badge className="border-cyan-300/20 bg-cyan-300/10 text-cyan-100">Ready now</Badge>
                <h2 className="mt-4 text-2xl font-semibold text-white">Start with a simple question.</h2>
                <p className="mt-3 text-sm leading-7 text-slate-300">
                  The copilot is best for translating complex signals into clear next steps: what happened, why it matters, what could go wrong, and where to look next.
                </p>
                <div className="mt-5 flex flex-wrap gap-2">
                  <Link href="/scanner"><Button size="sm" variant="secondary">Find setups</Button></Link>
                  <Link href="/reports"><Button size="sm" variant="secondary">Investment notes</Button></Link>
                </div>
              </div>
              <div className="space-y-3">
                {[
                  "Ask why the signal changed and what evidence moved it.",
                  "Check the biggest risks before making a paper-trade note.",
                  "Turn the current chart, news, and audit trail into plain English.",
                ].map((item) => (
                  <div key={item} className="flex gap-3 rounded-2xl border border-white/8 bg-white/4 p-4 text-sm leading-6 text-slate-300">
                    <IconWarning className="mt-0.5 h-4 w-4 shrink-0 text-amber-200" />
                    {item}
                  </div>
                ))}
                <div className="rounded-2xl border border-white/8 bg-slate-950/60 p-4 text-xs leading-5 text-slate-500">
                  AI is an explanation layer only. BUY/SELL calls still come from the deterministic signal engine and risk rules.
                </div>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge>{response.symbol}</Badge>
                <Badge>{response.source.replaceAll("_", " ")}</Badge>
                <Badge>{response.provenance.usesOpenAI ? "OpenAI server-side" : "local fallback"}</Badge>
              </div>
              <p className="mt-5 whitespace-pre-wrap rounded-[26px] border border-white/8 bg-slate-950/60 p-5 text-sm leading-7 text-slate-200">{response.answer}</p>
              <div className="mt-5 grid gap-3 md:grid-cols-2">
                <Link href={`/asset/${response.symbol}`}>
                  <Button className="w-full" variant="secondary">Open {response.symbol} research</Button>
                </Link>
                <Link href="/strategy-tester">
                  <Button className="w-full" variant="secondary">Check backtest assumptions</Button>
                </Link>
              </div>
              <div className="mt-5">
                <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Citations</p>
                <div className="mt-3 space-y-2">
                  {response.citations.map((item: string) => <div key={item} className="rounded-2xl border border-white/8 bg-white/4 p-3 text-sm text-slate-400">{item}</div>)}
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </AppFrame>
  );
}
