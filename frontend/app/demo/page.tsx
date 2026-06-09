"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import {
  TrendingUp, TrendingDown, Loader2, ArrowRight, Sparkles, BarChart3,
} from "lucide-react";
import { useCountUp } from "@/hooks/use-count-up";

const API_BASE = "https://quantflow-v3q5.onrender.com/api/v1";

interface DemoMeta {
  id: string; title: string; subtitle: string; total_return: number;
  sharpe_ratio: number; ticker: string;
}

interface DemoData {
  id: string; title: string; subtitle: string; story: string;
  ticker: string; strategy_type: string; strategy_params: Record<string, any>;
  total_return: number; annual_return: number; sharpe_ratio: number;
  sortino_ratio: number; max_drawdown: number; win_rate: number;
  profit_factor: number; total_trades: number;
  equity_curve: Array<{ date: string; value: number }>;
  trades: Array<{ entry_date: string; exit_date: string; side: string;
    entry_price: number; exit_price: number; return_pct: number; pnl: number }>;
}

function MetricCard({ label, value, isPct, color }: { label: string; value: number | null; isPct?: boolean; color?: string }) {
  const absVal = value != null ? Math.abs(value) : 0;
  const animated = useCountUp(absVal, 800, value != null);
  if (value == null) return null;
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111] p-4">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className={`mt-1 text-xl font-bold ${color || "text-white"}`}>
        {value < 0 ? "−" : ""}
        {isPct ? `${animated.toFixed(1)}%` : animated.toFixed(2)}
      </p>
    </div>
  );
}

// ── Interactive parameter teaser ──────────────────────────────────────────────

const TEASER_PARAMS: Record<string, { key: string; label: string; min: number; max: number; default: number; unit: string }> = {
  "qqq-donchian": { key: "entry_period", label: "Entry Period", min: 5, max: 55, default: 20, unit: "days" },
  "spy-momentum": { key: "threshold", label: "Threshold", min: 0.01, max: 0.2, default: 0.05, unit: "%" },
  "btc-dualma":   { key: "short_period", label: "Short Period", min: 2, max: 30, default: 5, unit: "days" },
};

function ParamTeaser({ data }: { data: DemoData | null }) {
  const [value, setValue] = useState<number | null>(null);
  const [showLock, setShowLock] = useState(false);

  if (!data) return null;
  const spec = TEASER_PARAMS[data.id];
  if (!spec) return null;

  const current = value ?? spec.default;
  const changed = current !== spec.default;

  return (
    <div className="rounded-2xl border border-dashed border-white/[0.08] bg-[#0f0f0f] p-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-zinc-300">
          🔧 Want better results? Try adjusting <span className="text-emerald-400">{spec.label}</span>
        </h3>
        {changed && <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-400">Preview only</span>}
      </div>

      <div className="flex items-center gap-4">
        <input
          type="range"
          min={spec.min}
          max={spec.max}
          step={spec.key === "threshold" ? 0.01 : 1}
          value={current}
          onChange={(e) => {
            setValue(parseFloat(e.target.value));
            if (!changed) setTimeout(() => setShowLock(true), 1200);
          }}
          className="flex-1 h-1.5 cursor-pointer rounded-full bg-white/[0.08] accent-emerald-500"
        />
        <span className="w-16 text-right text-sm font-mono text-white">
          {spec.key === "threshold" ? `${(current * 100).toFixed(0)}%` : current}
          <span className="text-xs text-zinc-500 ml-0.5">{spec.unit}</span>
        </span>
      </div>

      {changed && (
        <div className="mt-4 flex items-center justify-between rounded-lg bg-amber-500/[0.06] border border-amber-500/15 px-4 py-3">
          <p className="text-xs text-amber-400/80">
            <span className="font-semibold">🔓 Unlock full optimization</span> — test 100+ parameter combinations to find the best settings.
          </p>
          <Link href="/register" className="flex-shrink-0 rounded-lg bg-emerald-500 px-4 py-2 text-xs font-semibold text-black hover:bg-emerald-400">
            Sign Up Free →
          </Link>
        </div>
      )}

      {!changed && (
        <p className="mt-2 text-xs text-zinc-500">
          Drag the slider to see how parameters impact results. Sign up to run unlimited backtests with your own settings.
        </p>
      )}
    </div>
  );
}


export default function DemoPage() {
  const [demos, setDemos] = useState<DemoMeta[]>([]);
  const [activeId, setActiveId] = useState("qqq-donchian");
  const [data, setData] = useState<DemoData | null>(null);
  const [loading, setLoading] = useState(true);

  // Load demo list
  useEffect(() => {
    fetch(`${API_BASE}/demo/list`)
      .then((r) => r.json())
      .then((json) => {
        const list = json?.data?.demos ?? [];
        setDemos(list);
        if (list.length > 0 && !activeId) setActiveId(list[0].id);
      }).catch(() => {});
  }, []);

  // Load active demo
  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/demo/${activeId}`)
      .then((r) => r.json())
      .then((json) => setData(json?.data ?? json))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [activeId]);

  const isPositive = (data?.total_return ?? 0) >= 0;

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Top bar */}
      <header className="border-b border-white/[0.06] bg-[#0a0a0a]/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-lg font-bold text-emerald-400">Quant<span className="text-white">Flow</span></Link>
          <div className="flex items-center gap-3">
            <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs text-emerald-400">
              <Sparkles className="h-3 w-3" /> Live Demo
            </span>
            <Link href="/register" className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-black hover:bg-emerald-400">Sign Up Free</Link>
          </div>
        </div>
      </header>

      {/* Banner */}
      <div className="border-b border-white/[0.04] bg-emerald-500/[0.04]">
        <p className="mx-auto max-w-5xl px-6 py-3 text-center text-xs sm:text-sm text-emerald-400/80">
          🎬 This is real backtest data. <Link href="/register" className="underline hover:text-emerald-300 font-medium">Sign up</Link> to run your own strategies for free.
        </p>
      </div>

      <main className="mx-auto max-w-5xl px-6 py-8 space-y-8">
        {/* Demo tabs */}
        <div className="flex flex-wrap gap-2">
          {demos.map((d) => (
            <button
              key={d.id}
              onClick={() => setActiveId(d.id)}
              className={`rounded-xl px-4 py-2.5 text-xs sm:text-sm font-medium transition-all ${
                activeId === d.id
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                  : "border border-white/[0.06] text-zinc-400 hover:text-white hover:border-white/[0.15]"
              }`}
            >
              {d.ticker} · {d.title.split("·")[1]?.trim().split("(")[0]?.trim() || d.title}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
          </div>
        ) : data ? (
          <>
            {/* Story card */}
            <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-6">
              <h1 className="text-xl font-bold text-white">{data.title}</h1>
              <p className="mt-1 text-sm text-emerald-400">{data.subtitle}</p>
              <p className="mt-3 text-sm leading-relaxed text-zinc-400">{data.story}</p>
            </div>

            {/* Metrics */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <MetricCard label="Total Return" value={data.total_return} isPct color={isPositive ? "text-emerald-400" : "text-red-400"} />
              <MetricCard label="Annual Return" value={data.annual_return} isPct />
              <MetricCard label="Sharpe Ratio" value={data.sharpe_ratio} />
              <MetricCard label="Max Drawdown" value={data.max_drawdown} isPct color="text-red-400" />
              <MetricCard label="Win Rate" value={data.win_rate} isPct />
              <MetricCard label="Total Trades" value={data.total_trades} />
            </div>

            {/* Interactive parameter teaser */}
            <ParamTeaser data={data} />

            {/* Legal disclaimer */}
            <p className="text-center text-[11px] text-zinc-600">
              Past performance does not guarantee future results. Demo shows historically optimized parameters.
            </p>

            {/* Chart */}
            {data.equity_curve && data.equity_curve.length > 0 && (
              <div className="rounded-2xl border border-white/[0.06] bg-[#0f0f0f] p-6">
                <h2 className="mb-4 text-sm font-semibold text-zinc-300">Equity Curve</h2>
                <div className="h-[300px]">
                  <svg viewBox="0 0 800 300" className="h-full w-full" preserveAspectRatio="none">
                    <defs>
                      <linearGradient id="eGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
                        <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <polyline fill="none" stroke="#10b981" strokeWidth="2"
                      points={data.equity_curve.map((p, i) =>
                        `${(i / (data.equity_curve.length - 1)) * 800},${300 - (p.value / data.equity_curve[data.equity_curve.length - 1].value) * 280}`
                      ).join(" ")}
                    />
                  </svg>
                </div>
              </div>
            )}

            {/* Trades table */}
            {data.trades && data.trades.length > 0 && (
              <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-6 overflow-x-auto">
                <h2 className="mb-4 text-sm font-semibold text-zinc-300">Recent Trades ({data.trades.length})</h2>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-zinc-500">
                      <th className="pr-3 pb-2 text-left">Entry</th>
                      <th className="pr-3 pb-2 text-left">Exit</th>
                      <th className="pr-3 pb-2 text-right">Entry $</th>
                      <th className="pr-3 pb-2 text-right">Exit $</th>
                      <th className="pr-3 pb-2 text-right">Return</th>
                      <th className="pb-2 text-right">P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.trades.map((t, i) => (
                      <tr key={i} className="border-t border-white/[0.02] text-zinc-400">
                        <td className="pr-3 py-1.5 font-mono">{t.entry_date}</td>
                        <td className="pr-3 py-1.5 font-mono">{t.exit_date}</td>
                        <td className="pr-3 py-1.5 text-right font-mono">${t.entry_price.toFixed(2)}</td>
                        <td className="pr-3 py-1.5 text-right font-mono">${t.exit_price.toFixed(2)}</td>
                        <td className={`pr-3 py-1.5 text-right font-mono font-medium ${t.return_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                          {t.return_pct >= 0 ? "+" : ""}{t.return_pct.toFixed(2)}%
                        </td>
                        <td className={`py-1.5 text-right font-mono font-medium ${t.pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                          ${t.pnl.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        ) : (
          <div className="py-20 text-center">
            <BarChart3 className="mx-auto h-10 w-10 text-zinc-600" />
            <p className="mt-3 text-sm text-zinc-500">Demo not available. Please try again later.</p>
          </div>
        )}

        {/* CTA */}
        {data && (
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.04] p-10 text-center">
            <h2 className="text-xl font-bold text-white">Like what you see?</h2>
            <p className="mt-2 text-sm text-zinc-400">Test YOUR strategy in 60 seconds. 12 strategies, real market data.</p>
            <div className="mt-4 flex flex-col sm:flex-row items-center justify-center gap-3 text-xs text-zinc-500">
              <span className="flex items-center gap-1">✓ 5 free backtests/day</span>
              <span className="flex items-center gap-1">✓ 12 strategies</span>
              <span className="flex items-center gap-1">✓ No credit card</span>
            </div>
            <Link href="/register" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-8 py-3.5 text-base font-semibold text-black hover:bg-emerald-400">
              Start Backtesting Free <ArrowRight className="h-5 w-5" />
            </Link>
          </div>
        )}
      </main>

      <footer className="border-t border-white/[0.06] bg-[#0a0a0a] py-8 text-center text-xs text-zinc-600">
        Powered by <Link href="/" className="text-emerald-400 hover:text-emerald-300">QuantFlow</Link>
      </footer>
    </div>
  );
}
