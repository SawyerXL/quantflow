"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Search, TrendingUp, Zap, Loader2, Check, AlertTriangle,
  ArrowLeft, Sparkles, Lock,
} from "lucide-react";
import { API_URL } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";

type ParamSpec = { min?: number; max?: number; step?: number; values?: string[] };

// ============================================================
// Strategy presets for parameter ranges
// ============================================================
const PARAM_DEFAULTS: Record<string, Record<string, ParamSpec>> = {
  ma_cross: {
    fast_period:  { min: 5,  max: 20, step: 5 },
    slow_period:  { min: 20, max: 50, step: 10 },
    ma_type:      { values: ["sma", "ema"] },
  },
  rsi: {
    rsi_period:   { min: 5,  max: 20, step: 5 },
    oversold:     { min: 20, max: 40, step: 5 },
    overbought:   { min: 60, max: 80, step: 5 },
  },
  bollinger: {
    bb_period:    { min: 10, max: 30, step: 5 },
    bb_std:       { min: 1.0, max: 3.0, step: 0.5 },
  },
  macd: {
    fast_period:  { min: 8,  max: 20, step: 4 },
    slow_period:  { min: 20, max: 40, step: 5 },
    signal_period:{ min: 6,  max: 15, step: 3 },
  },
};

const METRICS = [
  { value: "sharpe_ratio", label: "Sharpe Ratio" },
  { value: "total_return", label: "Total Return" },
  { value: "max_drawdown", label: "Max Drawdown (min)" },
  { value: "win_rate", label: "Win Rate" },
  { value: "profit_factor", label: "Profit Factor" },
];

// ============================================================
// Heatmap component
// ============================================================
function Heatmap({ data }: { data: any }) {
  if (!data) return null;
  const { x_values, y_values, matrix, metric, x_param, y_param } = data;
  const flat = matrix.flat().filter((v: any) => v != null);
  const min = Math.min(...flat);
  const max = Math.max(...flat);

  function color(value: number | null) {
    if (value == null) return "bg-white/[0.02]";
    const ratio = (value - min) / (max - min || 1);
    if (ratio < 0.5) {
      const r = 239; const g = Math.round(68 + ratio * 2 * 119);
      return `rgb(${r},${g},68)`;
    }
    const r = Math.round(239 - (ratio - 0.5) * 2 * 205);
    const g = Math.round(197 - (ratio - 0.5) * 2 * 140);
    return `rgb(${r},${g},94)`;
  }

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111] p-4">
      <h3 className="mb-3 text-sm font-semibold text-zinc-300">Parameter Sensitivity Heatmap ({metric})</h3>
      <div className="overflow-x-auto">
        <table className="text-xs mx-auto">
          <thead>
            <tr>
              <th className="pr-3 text-zinc-500">{y_param} ↓ / {x_param} →</th>
              {x_values.map((x: any) => <th key={x} className="px-2 text-zinc-400">{x}</th>)}
            </tr>
          </thead>
          <tbody>
            {y_values.map((y: any, yi: number) => (
              <tr key={y}>
                <td className="pr-3 text-zinc-400">{y}</td>
                {x_values.map((x: any, xi: number) => {
                  const v = matrix[yi]?.[xi];
                  return (
                    <td key={x} className="p-1">
                      <div
                        className="w-16 h-8 rounded flex items-center justify-center text-zinc-200 font-mono"
                        style={{ background: color(v), color: v != null && (v - min) / (max - min) > 0.6 ? "#000" : "#fff" }}
                        title={v != null ? `${metric}: ${v.toFixed(3)}` : "N/A"}
                      >
                        {v != null ? v.toFixed(2) : "—"}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================
// Page
// ============================================================
export default function OptimizePage() {
  const { user } = useAuth();
  const router = useRouter();
  const plan = user?.plan || "free";
  const isLocked = plan === "free";

  const [ticker, setTicker] = useState("SPY");
  const [strategy, setStrategy] = useState("ma_cross");
  const [metric, setMetric] = useState("sharpe_ratio");
  const [paramRanges, setParamRanges] = useState<Record<string, ParamSpec>>(PARAM_DEFAULTS.ma_cross);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<{ total: number; max: number; exceeds: boolean; estimated_seconds: number } | null>(null);

  // Preview combo count
  const previewCombos = useCallback(async () => {
    const token = localStorage.getItem("token");
    if (!token) return;
    try {
      const res = await fetch(`${API_URL}/optimize/preview-count`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ strategy_type: strategy, param_ranges: paramRanges }),
      });
      const json = await res.json();
      const d = json.data ?? json;
      setPreview({ total: d.total_combinations, max: d.max_allowed, exceeds: d.exceeds_limit, estimated_seconds: d.estimated_seconds });
    } catch { /* ignore */ }
  }, [strategy, paramRanges]);

  // Run optimization
  const run = useCallback(async () => {
    setError("");
    setLoading(true);
    setResult(null);
    const token = localStorage.getItem("token");
    try {
      const res = await fetch(`${API_URL}/optimize/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ticker, strategy_type: strategy, param_ranges: paramRanges, optimize_metric: metric }),
      });
      const json = await res.json();
      if (json.success) {
        setResult(json.data);
      } else {
        setError(json.error?.message || json.detail?.message || "Optimization failed");
      }
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [ticker, strategy, paramRanges, metric]);

  // Apply best params → go to backtest
  const applyParams = () => {
    if (!result) return;
    const p = result.best_params;
    const qs = new URLSearchParams({ ticker, strategy_type: strategy });
    Object.entries(p).forEach(([k, v]) => qs.set(k, String(v)));
    router.push(`/backtest`);
  };

  return (
    <div className="space-y-6 pb-16">
      <Link href="/dashboard" className="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300">
        <ArrowLeft className="h-3 w-3" /> Dashboard
      </Link>
      <h1 className="text-2xl font-bold text-white">Parameter Optimization</h1>

      {/* Locked notice */}
      {isLocked && (
        <div className="flex items-center justify-between rounded-xl border border-amber-500/30 bg-amber-500/[0.06] px-5 py-4">
          <div className="flex items-center gap-3">
            <Lock className="h-5 w-5 text-amber-400" />
            <div>
              <p className="text-sm font-medium text-amber-400">Pro Feature</p>
              <p className="text-xs text-amber-400/70">Parameter optimization requires Pro ($19/mo) or Quant plan.</p>
            </div>
          </div>
          <Link href="/dashboard/billing" className="rounded-lg bg-amber-500 px-4 py-2 text-xs font-semibold text-black hover:bg-amber-400">
            Upgrade to Pro
          </Link>
        </div>
      )}

      {/* Config */}
      <div className="grid gap-8 lg:grid-cols-[1fr_420px]">
        <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-6 space-y-5">
          {/* Ticker */}
          <div>
            <label className="block mb-1.5 text-sm font-medium text-zinc-400">Ticker</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
              <input value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())} className="w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] py-2.5 pl-10 pr-4 text-sm text-white outline-none focus:border-emerald-500/50" />
            </div>
          </div>

          {/* Strategy */}
          <div>
            <label className="block mb-1.5 text-sm font-medium text-zinc-400">Strategy</label>
            <select value={strategy} onChange={e => { setStrategy(e.target.value); setParamRanges(PARAM_DEFAULTS[e.target.value] || {}); }} className="w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] py-2.5 px-4 text-sm text-white outline-none focus:border-emerald-500/50">
              <option value="ma_cross">MA Crossover</option>
              <option value="rsi">RSI</option>
              <option value="bollinger">Bollinger Bands</option>
              <option value="macd">MACD</option>
            </select>
          </div>

          {/* Parameter ranges */}
          <div>
            <label className="block mb-2 text-sm font-medium text-zinc-400">Parameter Ranges</label>
            <div className="space-y-3">
              {Object.entries(paramRanges).map(([key, spec]) => (
                <div key={key} className="flex items-center gap-3 text-xs">
                  <span className="w-28 text-zinc-400">{key}</span>
                  {spec.values ? (
                    <div className="flex flex-wrap gap-1.5">
                      {spec.values.map(v => (
                        <span key={v} className="rounded bg-white/[0.06] px-2 py-1 text-zinc-300">{v}</span>
                      ))}
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <input type="number" value={spec.min ?? ""} onChange={e => {
                        const v = parseFloat(e.target.value);
                        if (!isNaN(v)) { paramRanges[key] = { ...spec, min: v }; setParamRanges({ ...paramRanges }); previewCombos(); }
                      }} className="w-16 rounded-lg border border-white/[0.08] bg-[#0f0f0f] px-2 py-1 text-white" placeholder="Min" />
                      <span className="text-zinc-600">–</span>
                      <input type="number" value={spec.max ?? ""} onChange={e => {
                        const v = parseFloat(e.target.value);
                        if (!isNaN(v)) { paramRanges[key] = { ...spec, max: v }; setParamRanges({ ...paramRanges }); previewCombos(); }
                      }} className="w-16 rounded-lg border border-white/[0.08] bg-[#0f0f0f] px-2 py-1 text-white" placeholder="Max" />
                      <span className="text-zinc-600">×</span>
                      <input type="number" value={spec.step ?? ""} onChange={e => {
                        const v = parseFloat(e.target.value);
                        if (!isNaN(v)) { paramRanges[key] = { ...spec, step: v }; setParamRanges({ ...paramRanges }); previewCombos(); }
                      }} className="w-14 rounded-lg border border-white/[0.08] bg-[#0f0f0f] px-2 py-1 text-white" placeholder="Step" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Combo preview */}
          <button onClick={previewCombos} className="text-xs text-emerald-400 hover:text-emerald-300">Preview combination count</button>
          {preview && (
            <div className={`rounded-lg px-4 py-3 text-xs ${preview.exceeds ? "bg-red-500/10 text-red-400" : "bg-emerald-500/10 text-emerald-400"}`}>
              {preview.total} combinations · ~{preview.estimated_seconds}s · Limit: {preview.max}
            </div>
          )}

          {/* Metric selector */}
          <div>
            <label className="block mb-1.5 text-sm font-medium text-zinc-400">Optimize For</label>
            <select value={metric} onChange={e => setMetric(e.target.value)} className="w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] py-2.5 px-4 text-sm text-white outline-none focus:border-emerald-500/50">
              {METRICS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
          </div>

          {/* Run */}
          <button onClick={run} disabled={loading || isLocked} className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-400 py-3 text-sm font-semibold text-black disabled:opacity-50 disabled:cursor-not-allowed">
            {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Running Optimization...</> : <><Zap className="h-4 w-4" /> Run Optimization</>}
          </button>

          {error && <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-400"><AlertTriangle className="h-4 w-4" />{error}</div>}
        </div>

        {/* Results panel */}
        <div className="space-y-4">
          {result && (
            <>
              {/* Best params */}
              <div className="rounded-2xl border border-emerald-500/30 bg-[#111] p-6">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="h-5 w-5 text-emerald-400" />
                  <h3 className="text-sm font-semibold text-white">Best Parameters Found</h3>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {Object.entries(result.best_params).map(([k, v]) => (
                    <div key={k} className="flex justify-between rounded bg-white/[0.03] px-3 py-2">
                      <span className="text-zinc-400">{k}</span>
                      <span className="text-emerald-400 font-mono">{String(v)}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                  {Object.entries(result.best_metrics).slice(0, 3).map(([k, v]) => (
                    <div key={k} className="rounded bg-white/[0.03] px-2 py-1.5 text-center">
                      <div className="text-zinc-500">{k}</div>
                      <div className="text-white font-mono">{typeof v === "number" ? v.toFixed(2) : String(v)}</div>
                    </div>
                  ))}
                </div>
                <button onClick={applyParams} className="mt-4 w-full rounded-xl bg-emerald-500 py-2.5 text-sm font-semibold text-black hover:bg-emerald-400">
                  Apply These Parameters →
                </button>
              </div>

              {/* Overfitting warning */}
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-4 text-xs text-amber-400/80">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-amber-400">Avoid Overfitting</p>
                    <p className="mt-1">Best in-sample parameters may not perform well out-of-sample. Consider testing across different time periods, checking parameter stability, or using Walk-Forward analysis (available on Quant plan).</p>
                  </div>
                </div>
              </div>

              {/* Heatmap */}
              {result.heatmap_data && <Heatmap data={result.heatmap_data} />}

              {/* All results table */}
              <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-4 overflow-x-auto">
                <h3 className="mb-3 text-sm font-semibold text-zinc-300">All Results ({result.total_combinations})</h3>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-zinc-500">
                      {Object.keys(result.all_results[0].params).map((k: string) => <th key={k} className="pr-3 pb-2 text-left">{k}</th>)}
                      <th className="pr-3 pb-2 text-right">Sharpe</th>
                      <th className="pr-3 pb-2 text-right">Return</th>
                      <th className="pr-3 pb-2 text-right">MaxDD</th>
                      <th className="pb-2 text-right">Win%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.all_results.map((r: any, i: number) => (
                      <tr key={i} className={`border-t border-white/[0.02] ${i === 0 ? "text-emerald-400" : "text-zinc-400"}`}>
                        {Object.values(r.params).map((v: any, j: number) => <td key={j} className="pr-3 py-1.5 font-mono">{String(v)}</td>)}
                        <td className="pr-3 py-1.5 text-right font-mono">{r.sharpe_ratio.toFixed(2)}</td>
                        <td className="pr-3 py-1.5 text-right font-mono">{r.total_return.toFixed(1)}%</td>
                        <td className="pr-3 py-1.5 text-right font-mono">{r.max_drawdown.toFixed(1)}%</td>
                        <td className="py-1.5 text-right font-mono">{r.win_rate.toFixed(0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
