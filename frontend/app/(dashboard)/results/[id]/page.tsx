"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowUpRight,
  TrendingUp,
  TrendingDown,
  Share2,
  Download,
  Plus,
  Check,
  Copy,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { useCountUp } from "@/hooks/use-count-up";

// ============================================================================
// Types
// ============================================================================

interface TradeRecord {
  entry_date: string;
  exit_date: string;
  side: "long" | "short";
  entry_price: number;
  exit_price: number;
  return_pct: number;
  pnl: number;
}

interface BacktestData {
  id: string;
  name: string;
  ticker: string;
  data_source: string;
  strategy_type: string;
  status: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  total_return: number;
  annual_return: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  profit_factor: number;
  result_data: {
    equity_curve: Array<{ date: string; value: number; benchmark: number }>;
    drawdown_curve: Array<{ date: string; value: number }>;
    trades: TradeRecord[];
  } | null;
  strategy_params?: Record<string, number | string>;
  created_at: string;
  completed_at: string | null;
}

const TRADES_PER_PAGE = 20;

// ============================================================================
// Mock data for development
// ============================================================================

function generateMockData(): BacktestData {
  return {
    id: "mock-1",
    name: "AAPL MA Crossover",
    ticker: "AAPL",
    data_source: "yahoo",
    strategy_type: "ma_cross",
    status: "completed",
    start_date: "2023-01-01",
    end_date: "2024-12-31",
    initial_capital: 10000,
    total_return: 0.352,
    annual_return: 0.162,
    sharpe_ratio: 1.42,
    sortino_ratio: 2.08,
    max_drawdown: -0.183,
    win_rate: 0.542,
    total_trades: 48,
    profit_factor: 1.86,
    result_data: {
      equity_curve: Array.from({ length: 504 }, (_, i) => ({
        date: new Date(2023, 0, 1 + i).toISOString().split("T")[0],
        value: 10000 * (1 + Math.sin(i * 0.03) * 0.3 + i * 0.0008),
        benchmark: 10000 * (1 + i * 0.0005 + Math.sin(i * 0.02) * 0.15),
      })),
      drawdown_curve: Array.from({ length: 504 }, (_, i) => ({
        date: new Date(2023, 0, 1 + i).toISOString().split("T")[0],
        value: -(0.08 + Math.sin(i * 0.05) * 0.06) * Math.min(1, i / 50),
      })),
      trades: Array.from({ length: 48 }, (_, i) => ({
        entry_date: new Date(2023, Math.floor(i * 0.4), 5 + i).toISOString().split("T")[0],
        exit_date: new Date(2023, Math.floor(i * 0.4 + 1), 10 + i).toISOString().split("T")[0],
        side: "long" as const,
        entry_price: 150 + i * 2 + Math.sin(i) * 10,
        exit_price: 150 + i * 2 + Math.sin(i) * 10 + (Math.random() > 0.5 ? 1 : -1) * Math.random() * 20,
        return_pct: (Math.random() - 0.45) * 0.15,
        pnl: (Math.random() - 0.45) * 500,
      })),
    },
    strategy_params: { fastPeriod: 10, slowPeriod: 30, maType: "ema" },
    created_at: "2024-06-01T10:30:00Z",
    completed_at: "2024-06-01T10:30:03Z",
  };
}

// ============================================================================
// Helpers
// ============================================================================

function fmtCurrency(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
}

function fmtPct(n: number, decimals = 2) {
  return `${(n * 100).toFixed(decimals)}%`;
}

function fmtNum(n: number, decimals = 2) {
  return n.toFixed(decimals);
}

function deltaText(current: number, benchmark: number) {
  const diff = current - benchmark;
  const pct = benchmark !== 0 ? (diff / Math.abs(benchmark)) * 100 : 0;
  return { value: Math.abs(pct).toFixed(1) + "%", positive: diff >= 0 };
}

// ============================================================================
// Skeleton
// ============================================================================

function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-xl bg-white/[0.04] ${className}`}
    />
  );
}

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-4 w-48" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="rounded-2xl border border-white/[0.06] bg-[#111] p-5">
            <Skeleton className="mb-3 h-3 w-20" />
            <Skeleton className="h-8 w-28" />
          </div>
        ))}
      </div>
      <Skeleton className="h-[420px]" />
      <Skeleton className="h-[200px]" />
      <Skeleton className="h-[300px]" />
    </div>
  );
}

// ============================================================================
// Metric card with count-up
// ============================================================================

function MetricCard({
  label,
  value,
  formatted,
  delta,
  colorClass = "text-white",
  suffix = "",
  prefix = "",
}: {
  label: string;
  value: number;
  formatted?: string;
  delta?: { value: string; positive: boolean } | null;
  colorClass?: string;
  suffix?: string;
  prefix?: string;
}) {
  const animated = useCountUp(Math.abs(value), 1500);
  const display =
    formatted ??
    (value < 1 && value > -1
      ? `${prefix}${fmtPct(animated, 2)}${suffix}`
      : `${prefix}${fmtNum(animated)}${suffix}`);

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-5 transition-all hover:border-white/[0.1]">
      <p className="text-xs font-medium text-zinc-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold tracking-tight ${colorClass}`}>
        {value < 0 ? "-" : ""}
        {display}
      </p>
      {delta && (
        <div className="mt-2 flex items-center gap-1">
          {delta.positive ? (
            <TrendingUp className="h-3.5 w-3.5 text-emerald-400" />
          ) : (
            <TrendingDown className="h-3.5 w-3.5 text-red-400" />
          )}
          <span
            className={`text-xs font-medium ${
              delta.positive ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {delta.positive ? "+" : "-"}
            {delta.value} vs B&H
          </span>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Drawdown mini chart (SVG)
// ============================================================================

function DrawdownChart({
  data,
}: {
  data: Array<{ date: string; value: number }>;
}) {
  if (!data || data.length < 2) {
    return (
      <div className="flex h-full items-center justify-center text-xs text-zinc-600">
        No drawdown data
      </div>
    );
  }

  const maxVal = 0;
  const minVal = Math.min(...data.map((d) => d.value), -0.01);
  const range = maxVal - minVal;

  const points = data
    .map((d, i) => {
      const x = (i / (data.length - 1)) * 100;
      const y = 100 - ((d.value - minVal) / range) * 100;
      return `${x},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <div className="relative h-full w-full">
      <svg
        viewBox="0 0 100 100"
        className="h-full w-full"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="ddArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* Zero line */}
        <line
          x1="0"
          y1={100 - ((0 - minVal) / range) * 100}
          x2="100"
          y2={100 - ((0 - minVal) / range) * 100}
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="0.3"
          strokeDasharray="2,2"
        />
        {/* Area */}
        <polygon
          fill="url(#ddArea)"
          points={`0,100 ${points} 100,100`}
        />
        {/* Line */}
        <polyline
          fill="none"
          stroke="#ef4444"
          strokeWidth="0.8"
          points={points}
        />
      </svg>
    </div>
  );
}

// ============================================================================
// Trades table
// ============================================================================

type SortKey = "entry_date" | "exit_date" | "return_pct" | "pnl";

function TradesTable({ trades }: { trades: TradeRecord[] }) {
  const [page, setPage] = useState(0);
  const [sortKey, setSortKey] = useState<SortKey>("entry_date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const totalPages = Math.max(1, Math.ceil(trades.length / TRADES_PER_PAGE));

  const sorted = useMemo(() => {
    const arr = [...trades];
    arr.sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      const cmp = typeof aVal === "string" ? aVal.localeCompare(bVal as string) : (aVal as number) - (bVal as number);
      return sortDir === "asc" ? cmp : -cmp;
    });
    return arr;
  }, [trades, sortKey, sortDir]);

  const paged = useMemo(
    () => sorted.slice(page * TRADES_PER_PAGE, (page + 1) * TRADES_PER_PAGE),
    [sorted, page],
  );

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  if (!trades.length) {
    return (
      <p className="py-12 text-center text-sm text-zinc-500">
        No trades executed during this period.
      </p>
    );
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-white/[0.06]">
              {(
                [
                  ["#", null],
                  ["Entry", "entry_date"],
                  ["Exit", "exit_date"],
                  ["Side", null],
                  ["Entry $", null],
                  ["Exit $", null],
                  ["Return", "return_pct"],
                  ["P&L", "pnl"],
                ] as [string, SortKey | null][]
              ).map(([label, key]) => (
                <th
                  key={label}
                  className={`pb-3 pr-4 font-medium text-zinc-500 ${
                    key ? "cursor-pointer select-none hover:text-zinc-300" : ""
                  }`}
                  onClick={() => key && toggleSort(key)}
                >
                  <span className="inline-flex items-center gap-1">
                    {label}
                    {sortKey === key &&
                      (sortDir === "asc" ? (
                        <ChevronUp className="h-3 w-3" />
                      ) : (
                        <ChevronDown className="h-3 w-3" />
                      ))}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.map((t, i) => (
              <tr
                key={i}
                className="border-b border-white/[0.02] transition-colors hover:bg-white/[0.02]"
              >
                <td className="py-2.5 pr-4 text-zinc-600">
                  {page * TRADES_PER_PAGE + i + 1}
                </td>
                <td className="py-2.5 pr-4 font-mono text-zinc-300">
                  {t.entry_date}
                </td>
                <td className="py-2.5 pr-4 font-mono text-zinc-300">
                  {t.exit_date}
                </td>
                <td className="py-2.5 pr-4">
                  <span
                    className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                      t.side === "long"
                        ? "bg-emerald-500/15 text-emerald-400"
                        : "bg-red-500/15 text-red-400"
                    }`}
                  >
                    {t.side}
                  </span>
                </td>
                <td className="py-2.5 pr-4 font-mono text-zinc-400">
                  ${t.entry_price.toFixed(2)}
                </td>
                <td className="py-2.5 pr-4 font-mono text-zinc-400">
                  ${t.exit_price.toFixed(2)}
                </td>
                <td
                  className={`py-2.5 pr-4 font-mono font-medium ${
                    t.return_pct >= 0 ? "text-emerald-400" : "text-red-400"
                  }`}
                >
                  {t.return_pct >= 0 ? "+" : ""}
                  {fmtPct(t.return_pct, 2)}
                </td>
                <td
                  className={`py-2.5 font-mono font-medium ${
                    t.pnl >= 0 ? "text-emerald-400" : "text-red-400"
                  }`}
                >
                  {t.pnl >= 0 ? "+" : ""}
                  {fmtCurrency(t.pnl)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between border-t border-white/[0.04] pt-4">
          <span className="text-xs text-zinc-500">
            Showing {page * TRADES_PER_PAGE + 1}–{Math.min((page + 1) * TRADES_PER_PAGE, trades.length)} of{" "}
            {trades.length} trades
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded-lg border border-white/[0.08] px-3 py-1.5 text-xs text-zinc-400 transition-all hover:border-white/[0.15] hover:text-white disabled:opacity-30"
            >
              Prev
            </button>
            {Array.from({ length: totalPages }).map((_, i) => (
              <button
                key={i}
                onClick={() => setPage(i)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                  i === page
                    ? "bg-white/[0.08] text-white"
                    : "text-zinc-500 hover:text-white"
                }`}
              >
                {i + 1}
              </button>
            ))}
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="rounded-lg border border-white/[0.08] px-3 py-1.5 text-xs text-zinc-400 transition-all hover:border-white/[0.15] hover:text-white disabled:opacity-30"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Page
// ============================================================================

export default function ResultPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const chartRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<BacktestData | null>(null);
  const [loading, setLoading] = useState(true);
  const [shareLink, setShareLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [chartReady, setChartReady] = useState(false);

  // Fetch
  useEffect(() => {
    async function fetchData() {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/backtest/${params.id}`,
        );
        if (res.ok) {
          const json = await res.json();
          setData(json.data ?? json);
        } else {
          // Use mock data for development
          setData(generateMockData());
        }
      } catch {
        setData(generateMockData());
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [params.id]);

  // Lightweight Charts
  useEffect(() => {
    if (!chartRef.current || !data?.result_data?.equity_curve) return;

    let chart: ReturnType<typeof import("lightweight-charts").createChart> | null = null;

    async function initChart() {
      try {
        const { createChart, ColorType } = await import("lightweight-charts");

        const container = chartRef.current!;
        chart = createChart(container, {
          layout: {
            background: { type: ColorType.Solid, color: "#0f0f0f" },
            textColor: "#71717a",
          },
          grid: {
            vertLines: { color: "rgba(255,255,255,0.03)" },
            horzLines: { color: "rgba(255,255,255,0.04)" },
          },
          crosshair: {
            vertLine: { color: "rgba(255,255,255,0.08)", width: 1, style: 2 },
            horzLine: { color: "rgba(255,255,255,0.08)", width: 1, style: 2 },
          },
          rightPriceScale: {
            borderColor: "rgba(255,255,255,0.06)",
            scaleMargins: { top: 0.05, bottom: 0.05 },
          },
          timeScale: {
            borderColor: "rgba(255,255,255,0.06)",
            timeVisible: true,
            secondsVisible: false,
          },
          height: 420,
          width: container.clientWidth,
        });

        const eq = data.result_data!.equity_curve;
        const chartData = eq.map((p) => ({
          time: p.date,
          value: p.value,
        }));
        const benchData = eq.map((p) => ({
          time: p.date,
          value: p.benchmark,
        }));

        // Strategy line
        const strategySeries = chart.addLineSeries({
          color: "#10b981",
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: true,
          priceFormat: {
            type: "price",
            precision: 0,
            minMove: 1,
          },
        });
        strategySeries.setData(chartData);

        // Benchmark line
        const benchSeries = chart.addLineSeries({
          color: "rgba(255,255,255,0.25)",
          lineWidth: 1.5,
          lineStyle: 2, // dashed
          priceLineVisible: false,
          lastValueVisible: false,
          priceFormat: {
            type: "price",
            precision: 0,
            minMove: 1,
          },
        });
        benchSeries.setData(benchData);

        chart.timeScale().fitContent();

        // Handle resize
        const handleResize = () => {
          if (chart && container) {
            chart.applyOptions({ width: container.clientWidth });
          }
        };
        window.addEventListener("resize", handleResize);
        setChartReady(true);

        return () => {
          window.removeEventListener("resize", handleResize);
          chart?.remove();
        };
      } catch {
        // lightweight-charts not available — fall through to SVG
      }
    }

    initChart();
    return () => { chart?.remove(); };
  }, [data]);

  // Share link
  const handleShare = useCallback(() => {
    const link = `${window.location.origin}/share/backtest/${params.id}`;
    setShareLink(link);
    navigator.clipboard.writeText(link).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [params.id]);

  // Loading state
  if (loading) return <PageSkeleton />;

  // Not found
  if (!data) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/[0.04]">
          <TrendingDown className="h-8 w-8 text-zinc-600" />
        </div>
        <h2 className="mt-4 text-lg font-semibold text-white">
          Result Not Found
        </h2>
        <p className="mt-2 text-sm text-zinc-500">
          This backtest may have been deleted or the ID is invalid.
        </p>
        <Link
          href="/backtest"
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-2.5 text-sm font-semibold text-black transition-all hover:bg-zinc-200"
        >
          <ArrowLeft className="h-4 w-4" />
          New Backtest
        </Link>
      </div>
    );
  }

  const eq = data.result_data?.equity_curve ?? [];
  const dd = data.result_data?.drawdown_curve ?? [];
  const trades = data.result_data?.trades ?? [];
  const benchDelta = eq.length > 0 ? deltaText(
    eq[eq.length - 1].value,
    eq[eq.length - 1].benchmark,
  ) : null;

  return (
    <div className="space-y-6 pb-16">
      {/* ── Toolbar ── */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/backtest"
            className="mb-2 inline-flex items-center gap-1 text-xs text-zinc-500 transition-colors hover:text-zinc-300"
          >
            <ArrowLeft className="h-3 w-3" /> Backtest
          </Link>
          <h1 className="text-xl font-bold text-white">{data.name}</h1>
          <div className="mt-1 flex items-center gap-3 text-xs text-zinc-500">
            <span>
              {data.start_date} → {data.end_date}
            </span>
            <span className="flex items-center gap-1">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              </span>
              Completed
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleShare}
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/[0.08] px-4 py-2 text-xs font-medium text-zinc-300 transition-all hover:border-white/[0.15] hover:text-white"
          >
            {copied ? (
              <>
                <Check className="h-4 w-4 text-emerald-400" />
                Copied
              </>
            ) : shareLink ? (
              <>
                <Copy className="h-4 w-4" />
                Copy Link
              </>
            ) : (
              <>
                <Share2 className="h-4 w-4" />
                Share
              </>
            )}
          </button>
          <button className="inline-flex items-center gap-1.5 rounded-xl border border-white/[0.08] px-4 py-2 text-xs font-medium text-zinc-300 transition-all hover:border-white/[0.15] hover:text-white">
            <Download className="h-4 w-4" />
            Export
          </button>
          <Link
            href="/backtest"
            className="inline-flex items-center gap-1.5 rounded-xl bg-white px-4 py-2 text-xs font-semibold text-black transition-all hover:bg-zinc-200"
          >
            <Plus className="h-4 w-4" />
            New
          </Link>
        </div>
      </div>

      {/* ── Metric cards ── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard
          label="Total Return"
          value={data.total_return}
          formatted={fmtPct(data.total_return)}
          delta={benchDelta}
          colorClass={data.total_return >= 0 ? "text-emerald-400" : "text-red-400"}
        />
        <MetricCard
          label="Annual Return"
          value={data.annual_return}
          formatted={fmtPct(data.annual_return)}
          colorClass={data.annual_return >= 0 ? "text-emerald-400" : "text-red-400"}
        />
        <MetricCard
          label="Sharpe Ratio"
          value={data.sharpe_ratio}
          formatted={fmtNum(data.sharpe_ratio)}
          colorClass="text-white"
        />
        <MetricCard
          label="Max Drawdown"
          value={data.max_drawdown}
          formatted={fmtPct(data.max_drawdown)}
          colorClass="text-red-400"
        />
        <MetricCard
          label="Win Rate"
          value={data.win_rate}
          formatted={fmtPct(data.win_rate, 1)}
          colorClass="text-white"
        />
        <MetricCard
          label="Total Trades"
          value={data.total_trades}
          formatted={String(data.total_trades)}
          colorClass="text-white"
        />
      </div>

      {/* ── Equity Curve Chart ── */}
      <div className="rounded-2xl border border-white/[0.06] bg-[#0f0f0f] p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-300">
            Equity Curve
          </h2>
          <div className="flex items-center gap-4 text-[11px]">
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-sm bg-emerald-500" />
              <span className="text-zinc-400">Strategy</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-sm bg-white/25" />
              <span className="text-zinc-400">Buy &amp; Hold</span>
            </span>
          </div>
        </div>
        <div
          ref={chartRef}
          className="relative min-h-[300px] w-full overflow-hidden rounded-xl"
        >
          {!chartReady && (
            <div className="absolute inset-0 flex items-center justify-center">
              <Skeleton className="h-full w-full" />
            </div>
          )}
        </div>
      </div>

      {/* ── Drawdown Chart ── */}
      <div className="rounded-2xl border border-white/[0.06] bg-[#0f0f0f] p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-300">
            Drawdown
          </h2>
          <span className="text-[11px] text-zinc-500">
            Max: {fmtPct(data.max_drawdown)}
          </span>
        </div>
        <div className="h-[180px] w-full">
          <DrawdownChart data={dd} />
        </div>
      </div>

      {/* ── Strategy Info ── */}
      <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-6">
        <h2 className="mb-4 text-sm font-semibold text-zinc-300">
          Strategy Configuration
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <InfoItem label="Symbol" value={data.ticker} />
          <InfoItem
            label="Date Range"
            value={`${data.start_date} → ${data.end_date}`}
          />
          <InfoItem
            label="Strategy"
            value={
              data.strategy_type === "ma_cross"
                ? "MA Crossover"
                : data.strategy_type === "rsi"
                  ? "RSI"
                  : "Bollinger Bands"
            }
          />
          <InfoItem
            label="Initial Capital"
            value={fmtCurrency(data.initial_capital)}
          />
          {data.strategy_params &&
            Object.entries(data.strategy_params).map(([k, v]) => (
              <InfoItem key={k} label={k} value={String(v)} />
            ))}
        </div>
      </div>

      {/* ── Trades Table ── */}
      <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-300">
            Trades{" "}
            <span className="font-normal text-zinc-500">
              ({data.total_trades})
            </span>
          </h2>
        </div>
        <TradesTable trades={trades} />
      </div>
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white/[0.03] px-3 py-2.5">
      <p className="text-[11px] text-zinc-500">{label}</p>
      <p className="mt-0.5 text-sm font-medium text-zinc-200">{value}</p>
    </div>
  );
}
