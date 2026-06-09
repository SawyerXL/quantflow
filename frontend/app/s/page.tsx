"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  TrendingUp,
  TrendingDown,
  Eye,
  BarChart3,
  ArrowRight,
  Loader2,
} from "lucide-react";
import { useCountUp } from "@/hooks/use-count-up";

// ============================================================================
// Types
// ============================================================================

interface SharedData {
  name: string;
  ticker: string;
  strategy_type: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  total_return: number | null;
  annual_return: number | null;
  sharpe_ratio: number | null;
  max_drawdown: number | null;
  win_rate: number | null;
  total_trades: number | null;
  profit_factor: number | null;
  result_data: {
    equity_curve?: Array<{ date: string; value: number; benchmark: number }>;
    drawdown_curve?: Array<{ date: string; value: number }>;
  } | null;
  view_count: number;
  created_at: string | null;
}

const API_BASE = "https://quantflow-v3q5.onrender.com/api/v1";

// ============================================================================
// Helpers
// ============================================================================

function MetricCard({
  label,
  value,
  isPct = false,
  color = "text-white",
}: {
  label: string;
  value: number | null;
  isPct?: boolean;
  color?: string;
}) {
  const absVal = value != null ? Math.abs(value) : 0;
  const animated = useCountUp(absVal, 1000, value != null);

  if (value == null) return null;

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111] p-5">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${color}`}>
        {value < 0 ? "−" : ""}
        {isPct ? `${animated.toFixed(1)}%` : animated.toFixed(2)}
      </p>
    </div>
  );
}

// ============================================================================

function SharedPageInner() {
  const searchParams = useSearchParams();
  const slug = searchParams.get("slug") || "";
  const [data, setData] = useState<SharedData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!slug) { setError("No share link provided"); setLoading(false); return; }
    fetch(`${API_BASE}/share/${slug}`)
      .then((r) => r.json())
      .then((json) => {
        const d = json.data ?? json;
        if (json.success || d.name) {
          setData(d);
        } else {
          setError(json.error?.message || json.detail?.message || "Not found");
        }
      })
      .catch(() => setError("Failed to load. Please try again."))
      .finally(() => setLoading(false));
  }, [slug]);

  // Loading
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0a0a0a]">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  // Error / Not found
  if (error || !data) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-[#0a0a0a] px-4 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/[0.04]">
          <BarChart3 className="h-8 w-8 text-zinc-600" />
        </div>
        <h1 className="mt-4 text-xl font-bold text-white">
          {error || "Shared backtest not found"}
        </h1>
        <p className="mt-2 text-sm text-zinc-500">
          This link may have expired or been revoked.
        </p>
        <Link
          href="/"
          className="mt-6 rounded-xl bg-emerald-500 px-6 py-3 text-sm font-semibold text-black hover:bg-emerald-400"
        >
          Try QuantFlow Free
        </Link>
      </div>
    );
  }

  const isPositive = (data.total_return ?? 0) >= 0;

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Top bar */}
      <header className="border-b border-white/[0.06] bg-[#0a0a0a]/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-lg font-bold text-emerald-400">
            Quant<span className="text-white">Flow</span>
          </Link>
          <Link
            href="/register"
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-black hover:bg-emerald-400"
          >
            Sign Up Free
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-10 space-y-8">
        {/* Meta */}
        <div className="flex items-center gap-4 text-sm text-zinc-500">
          <span className="inline-flex items-center gap-1">
            🔗 Shared Backtest
          </span>
          <span className="inline-flex items-center gap-1">
            <Eye className="h-3.5 w-3.5" /> {data.view_count} views
          </span>
        </div>

        {/* Title */}
        <div>
          <h1 className="text-2xl font-bold text-white">{data.name}</h1>
          <p className="mt-1 text-sm text-zinc-400">
            {data.ticker} · {data.strategy_type} · {data.start_date} → {data.end_date}
          </p>
        </div>

        {/* Metrics */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <MetricCard
            label="Total Return"
            value={data.total_return != null ? data.total_return * 100 : null}
            isPct
            color={isPositive ? "text-emerald-400" : "text-red-400"}
          />
          <MetricCard
            label="Annual Return"
            value={data.annual_return != null ? data.annual_return * 100 : null}
            isPct
            color={(data.annual_return ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}
          />
          <MetricCard label="Sharpe Ratio" value={data.sharpe_ratio} />
          <MetricCard label="Max Drawdown" value={data.max_drawdown != null ? data.max_drawdown * 100 : null} isPct color="text-red-400" />
          <MetricCard label="Win Rate" value={data.win_rate != null ? data.win_rate * 100 : null} isPct />
          <MetricCard label="Total Trades" value={data.total_trades} />
        </div>

        {/* Equity Chart */}
        {data.result_data?.equity_curve && data.result_data.equity_curve.length > 0 && (
          <div className="rounded-2xl border border-white/[0.06] bg-[#0f0f0f] p-6">
            <h2 className="mb-4 text-sm font-semibold text-zinc-300">Equity Curve</h2>
            <div className="h-[320px]">
              <svg viewBox="0 0 800 300" className="h-full w-full" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
                  </linearGradient>
                </defs>
                {/* Strategy line */}
                <polyline
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="2"
                  points={data.result_data.equity_curve.map((p, i) =>
                    `${(i / (data.result_data!.equity_curve!.length - 1)) * 800},${300 - (p.value / data.result_data!.equity_curve![data.result_data!.equity_curve!.length - 1].value) * 280}`
                  ).join(" ")}
                />
              </svg>
            </div>
          </div>
        )}

        {/* CTA */}
        <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-10 text-center">
          <h2 className="text-xl font-bold text-white">Want to test your own strategy?</h2>
          <p className="mt-2 text-sm text-zinc-400">
            Run unlimited backtests for free. No credit card required.
          </p>
          <Link
            href="/register"
            className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-8 py-3.5 text-base font-semibold text-black hover:bg-emerald-400"
          >
            Start Backtesting Free <ArrowRight className="h-5 w-5" />
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/[0.06] bg-[#0a0a0a] py-8 text-center text-xs text-zinc-600">
        Powered by{" "}
        <Link href="/" className="text-emerald-400 hover:text-emerald-300">QuantFlow</Link>
        {" · "} Quantitative Backtesting Platform
      </footer>
    </div>
  );
}

export default function SharedPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-[#0a0a0a]">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      </div>
    }>
      <SharedPageInner />
    </Suspense>
  );
}
