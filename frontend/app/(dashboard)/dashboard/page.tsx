"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  BarChart3,
  TrendingUp,
  Activity,
  Clock,
  Plus,
  Play,
  ArrowRight,
  Zap,
  Sparkles,
  Loader2,
  Trash2,
} from "lucide-react";
import { API_URL } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import { useCountUp } from "@/hooks/use-count-up";

// ============================================================================
// Types
// ============================================================================

interface RecentItem {
  id: string;
  name: string;
  ticker: string;
  total_return: number | null;
  sharpe_ratio: number | null;
  win_rate: number | null;
  created_at: string | null;
}

interface DashboardData {
  has_data: boolean;
  total_backtests: number;
  backtests_today: number;
  stats: {
    avg_sharpe: number;
    avg_return: number;
    best_return: number | null;
    best_name: string | null;
    best_ticker: string | null;
    recent: RecentItem[];
  } | null;
}

// ============================================================================
// Quick-start templates
// ============================================================================

const TEMPLATES = [
  { ticker: "AAPL", strategy: "ma_cross", label: "AAPL × MA Crossover", desc: "Trend-following on Apple (2020–2024)" },
  { ticker: "SPY", strategy: "rsi", label: "SPY × RSI", desc: "Mean-reversion on S&P 500 ETF" },
  { ticker: "QQQ", strategy: "bollinger", label: "QQQ × Bollinger", desc: "Volatility breakout on Nasdaq 100" },
];

async function fetchDashboard(token: string): Promise<DashboardData> {
  const res = await fetch(`${API_URL}/dashboard/stats`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const json = await res.json();
  return (json.data ?? json) as DashboardData;
}

// ============================================================================
// Stats card skeleton
// ============================================================================

function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-xl bg-white/[0.04] ${className}`} />;
}

function StatCard({
  title,
  value,
  subtitle,
  loading,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  loading?: boolean;
}) {
  const num = typeof value === "number" ? value : parseFloat(String(value));
  const animated = useCountUp(isNaN(num) ? 0 : num, 800, !loading && !isNaN(num));

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-5 transition-all hover:border-white/[0.1]">
      <p className="text-xs font-medium text-zinc-500">{title}</p>
      {loading ? (
        <Skeleton className="mt-1.5 h-8 w-24" />
      ) : (
        <p className="mt-1 text-2xl font-bold tracking-tight text-white">
          {typeof value === "number" && value < 1 && value > -1
            ? `${(animated * 100).toFixed(1)}%`
            : animated % 1 === 0
              ? animated.toLocaleString()
              : animated.toFixed(2)}
        </p>
      )}
      {subtitle && <p className="mt-1 text-xs text-zinc-500">{subtitle}</p>}
    </div>
  );
}

// ============================================================================
// Page
// ============================================================================

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const token = localStorage.getItem("token");
    if (!token) { setLoading(false); return; }
    try {
      const d = await fetchDashboard(token);
      setData(d);
    } catch { /* keep loading */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  // ── Empty state ──
  if (!loading && (!data || !data.has_data)) {
    return (
      <div className="space-y-8">
        <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-10 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-500/10">
            <Sparkles className="h-8 w-8 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Welcome to QuantFlow!</h1>
          <p className="mt-2 text-sm text-zinc-400 max-w-md mx-auto">
            You haven&apos;t run any backtests yet. Start by choosing a stock and a strategy — results appear here instantly.
          </p>

          {/* Steps */}
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            {[
              { num: 1, label: "Choose Ticker & Strategy" },
              { num: 2, label: "Run Backtest" },
              { num: 3, label: "View Results" },
            ].map((s) => (
              <div key={s.num} className="flex items-center gap-3 rounded-xl bg-white/[0.03] px-5 py-4">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500/20 text-sm font-bold text-emerald-400">
                  {s.num}
                </span>
                <span className="text-sm font-medium text-zinc-300">{s.label}</span>
              </div>
            ))}
          </div>

          <Link href="/backtest" className="mt-8 inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-6 py-3 text-sm font-semibold text-black transition-all hover:bg-emerald-400">
            <Play className="h-4 w-4 fill-black" />
            Run Your First Backtest
          </Link>

          {/* Templates */}
          <div className="mt-10">
            <p className="mb-4 text-xs font-medium uppercase tracking-wider text-zinc-600">
              Or try an example
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              {TEMPLATES.map((t) => (
                <Link
                  key={t.label}
                  href={`/backtest`}
                  className="group flex items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] px-5 py-3 transition-all hover:border-emerald-500/30 hover:bg-white/[0.04]"
                >
                  <div>
                    <p className="text-sm font-medium text-zinc-300">{t.label}</p>
                    <p className="text-xs text-zinc-500">{t.desc}</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-zinc-600 group-hover:text-emerald-400" />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Data state ──
  const stats = data?.stats;
  const limit = user?.plan === "free" ? 5 : "∞";
  const used = data?.backtests_today ?? 0;

  const deleteBacktest = async (id: string) => {
    const token = localStorage.getItem("token");
    if (!token) return;
    await fetch(`${API_URL}/backtest/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    load(); // Refresh the list
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Welcome back{user?.full_name ? `, ${user.full_name}` : ""}
          </p>
        </div>
        <Link href="/backtest" className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-black transition-all hover:bg-emerald-400">
          <Plus className="h-4 w-4" />
          New Backtest
        </Link>
      </div>

      {/* Stats grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Backtests" value={data?.total_backtests ?? 0} loading={loading} />
        <StatCard
          title="Best Return"
          value={stats?.best_return != null ? stats.best_return : "--"}
          subtitle={stats?.best_name ? `${stats.best_ticker} · ${stats.best_name}` : undefined}
          loading={loading}
        />
        <StatCard title="Avg Sharpe" value={stats?.avg_sharpe ?? "--"} loading={loading} />
        <StatCard
          title="Backtests Today"
          value={`${used}/${limit}`}
          subtitle={user?.plan === "free" ? "Free plan" : "Unlimited"}
          loading={loading}
        />
      </div>

      {/* Recent backtests */}
      <div>
        <h2 className="mb-4 text-lg font-semibold text-white">Recent Backtests</h2>
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
          </div>
        ) : !stats?.recent?.length ? (
          <div className="rounded-2xl border border-white/[0.06] bg-[#111] py-12 text-center">
            <BarChart3 className="mx-auto h-8 w-8 text-zinc-600" />
            <p className="mt-3 text-sm text-zinc-500">No completed backtests yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {stats.recent.map((r) => (
              <div
                key={r.id}
                className="flex items-center justify-between rounded-xl border border-white/[0.04] bg-[#111] px-5 py-4 transition-all hover:border-white/[0.1] hover:bg-[#161616]"
              >
                <Link href={`/results?id=${r.id}`} className="flex items-center gap-4 flex-1 min-w-0">
                  <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-emerald-500/10">
                    <TrendingUp className="h-4 w-4 text-emerald-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white truncate">{r.name}</p>
                    <p className="text-xs text-zinc-500">
                      {r.ticker} · Sharpe {r.sharpe_ratio?.toFixed(2) ?? "--"} · Win {r.win_rate != null ? `${(r.win_rate * 100).toFixed(0)}%` : "--"}
                    </p>
                  </div>
                </Link>
                <div className="flex items-center gap-4">
                  <div className="text-right hidden sm:block">
                    <p className={`text-sm font-semibold ${(r.total_return ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                      {r.total_return != null ? `${r.total_return >= 0 ? "+" : ""}${(r.total_return * 100).toFixed(1)}%` : "--"}
                    </p>
                    <p className="text-xs text-zinc-500">
                      {r.created_at ? new Date(r.created_at).toLocaleDateString() : ""}
                    </p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteBacktest(r.id); }}
                    className="p-2 rounded-lg text-zinc-600 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
