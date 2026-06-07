"use client";

import { useCallback, useMemo, useState, useRef, type DragEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Upload,
  Search,
  TrendingUp,
  BarChart3,
  Activity,
  Play,
  Loader2,
  Check,
  ChevronRight,
  ChevronLeft,
  FileText,
  AlertCircle,
  ArrowLeft,
} from "lucide-react";
import { useBacktestStore } from "@/stores/backtest-store";
import type { DataSource, StrategyType } from "@/stores/backtest-store";
import { API_URL } from "@/lib/api";

// ============================================================================
// Helpers
// ============================================================================

const STRATEGY_META: Record<
  StrategyType,
  { title: string; desc: string; icon: typeof TrendingUp }
> = {
  ma_cross: {
    title: "MA Crossover",
    desc: "Buy when fast MA crosses above slow MA. Classic trend-following.",
    icon: TrendingUp,
  },
  rsi: {
    title: "RSI Strategy",
    desc: "Buy oversold, sell overbought. Mean-reversion for range markets.",
    icon: Activity,
  },
  bollinger: {
    title: "Bollinger Bands",
    desc: "Buy at lower band, sell at upper band. Volatility mean-reversion.",
    icon: BarChart3,
  },
};

const PRESET_DATES = [
  { label: "1Y", get: () => yearsAgo(1) },
  { label: "2Y", get: () => yearsAgo(2) },
  { label: "5Y", get: () => yearsAgo(5) },
  { label: "Max", get: () => "2010-01-01" },
];

function today() {
  return new Date().toISOString().split("T")[0];
}
function yearsAgo(n: number) {
  const d = new Date();
  d.setFullYear(d.getFullYear() - n);
  return d.toISOString().split("T")[0];
}

// ============================================================================
// Step indicator
// ============================================================================

const STEPS = [
  { num: 1, label: "Data Source" },
  { num: 2, label: "Strategy" },
  { num: 3, label: "Parameters" },
  { num: 4, label: "Run" },
];

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-2">
      {STEPS.map((s, i) => (
        <div key={s.num} className="flex items-center gap-2">
          <div
            className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-all ${
              current > s.num
                ? "bg-emerald-500 text-white"
                : current === s.num
                  ? "bg-emerald-600 text-white ring-2 ring-emerald-500/50"
                  : "bg-white/[0.05] text-zinc-500"
            }`}
          >
            {current > s.num ? <Check className="h-4 w-4" /> : s.num}
          </div>
          <span
            className={`hidden text-xs font-medium sm:inline ${
              current >= s.num ? "text-zinc-200" : "text-zinc-600"
            }`}
          >
            {s.label}
          </span>
          {i < STEPS.length - 1 && (
            <div
              className={`hidden h-px w-8 sm:block ${
                current > s.num ? "bg-emerald-500" : "bg-white/[0.08]"
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Step 1: Data source
// ============================================================================

function DataSourceStep() {
  const store = useBacktestStore();

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex rounded-xl bg-white/[0.04] p-1">
        {(["ticker", "csv"] as DataSource[]).map((src) => (
          <button
            key={src}
            onClick={() => store.setDataSource(src)}
            className={`flex-1 rounded-lg py-2.5 text-sm font-medium transition-all ${
              store.dataSource === src
                ? "bg-white/[0.08] text-white shadow-sm"
                : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {src === "csv" ? "Upload CSV" : "Enter Ticker"}
          </button>
        ))}
      </div>

      {store.dataSource === "ticker" ? <TickerPanel /> : <CSVPanel />}
    </div>
  );
}

function TickerPanel() {
  const store = useBacktestStore();

  return (
    <div className="space-y-5">
      {/* Ticker input */}
      <div>
        <label className="mb-1.5 block text-sm font-medium text-zinc-400">
          Ticker Symbol
        </label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
          <input
            type="text"
            value={store.ticker.symbol}
            onChange={(e) => store.setTicker({ symbol: e.target.value.toUpperCase() })}
            placeholder="e.g., AAPL, SPY, BTC-USD"
            className="w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] py-2.5 pl-10 pr-4 text-sm text-white placeholder-zinc-600 outline-none transition-all focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30"
          />
        </div>
      </div>

      {/* Date range */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-zinc-400">
            Start Date
          </label>
          <input
            type="date"
            value={store.ticker.startDate}
            onChange={(e) => store.setTicker({ startDate: e.target.value })}
            className="w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] px-3 py-2.5 text-sm text-white outline-none transition-all focus:border-emerald-500/50"
          />
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-zinc-400">
            End Date
          </label>
          <input
            type="date"
            value={store.ticker.endDate}
            onChange={(e) => store.setTicker({ endDate: e.target.value })}
            className="w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] px-3 py-2.5 text-sm text-white outline-none transition-all focus:border-emerald-500/50"
          />
        </div>
      </div>

      {/* Presets */}
      <div className="flex flex-wrap gap-2">
        {PRESET_DATES.map((p) => (
          <button
            key={p.label}
            onClick={() =>
              store.setTicker({ startDate: p.get(), endDate: today() })
            }
            className="rounded-lg border border-white/[0.06] px-3 py-1.5 text-xs font-medium text-zinc-400 transition-all hover:border-white/[0.15] hover:text-white"
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function CSVPanel() {
  const store = useBacktestStore();
  const preview = store.csvPreview;
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState("");
  const [parseError, setParseError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  function parseCSV(text: string) {
    try {
      const lines = text.trim().split("\n");
      if (lines.length < 2) throw new Error("CSV file has no data rows");
      const headers = lines[0].split(",").map((h) => h.trim().replace(/^"|"$/g, ""));
      const closeIdx = headers.findIndex((h) => h.toLowerCase() === "close");
      const dateIdx = headers.findIndex((h) =>
        ["date", "datetime", "time", "timestamp"].includes(h.toLowerCase()),
      );

      const errors: string[] = [];
      let negCount = 0;
      let missingCount = 0;
      let firstNegRow = 0;
      let firstMissingRow = 0;

      // Parse all rows for data validation
      const allRows: Record<string, string>[] = [];
      for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(",").map((c) => c.trim().replace(/^"|"$/g, ""));
        const obj: Record<string, string> = {};
        headers.forEach((h, j) => (obj[h] = cols[j] ?? ""));
        allRows.push(obj);

        if (closeIdx >= 0) {
          const closeVal = cols[closeIdx];
          if (closeVal === "" || closeVal === undefined || closeVal === "None" || closeVal === "NaN") {
            if (missingCount === 0) firstMissingRow = i;
            missingCount++;
          } else {
            const num = Number(closeVal);
            if (!isNaN(num) && num <= 0) {
              if (negCount === 0) firstNegRow = i;
              negCount++;
            }
          }
        }
      }

      // Build errors
      if (closeIdx < 0) errors.push("Missing 'close' price column");
      if (dateIdx < 0) errors.push("Missing date/time column");
      if (negCount > 0) errors.push(`${negCount} negative/zero price(s) — first at row ${firstNegRow}`);
      if (missingCount > 0) errors.push(`${missingCount} missing close value(s) — first at row ${firstMissingRow}`);

      const valid = errors.length === 0;

      // Preview first 5 rows
      const previewRows = allRows.slice(0, 5);

      store.setCSVPreview({
        columns: headers,
        rows: previewRows,
        rowCount: lines.length - 1,
        valid,
        errors,
      });
      setParseError("");
    } catch (e: any) {
      setParseError(e.message || "Failed to parse CSV");
    }
  }

  function handleFile(file: File) {
    setParseError("");
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setParseError("Only CSV files are supported");
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setParseError("File too large (max 50 MB)");
      return;
    }
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = () => parseCSV(reader.result as string);
    reader.onerror = () => setParseError("Failed to read file");
    reader.readAsText(file);
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFile(file);
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    setDragOver(true);
  }

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={handleDragOver}
        onDragEnter={() => setDragOver(true)}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition-all ${
          dragOver
            ? "border-emerald-500/60 bg-emerald-500/[0.08]"
            : "border-white/[0.08] bg-[#0f0f0f] hover:border-emerald-500/30 hover:bg-[#121212]"
        }`}
      >
        <div
          className={`flex h-12 w-12 items-center justify-center rounded-xl transition-all ${
            dragOver ? "bg-emerald-500/30" : "bg-emerald-500/10"
          }`}
        >
          <Upload className={`h-6 w-6 ${dragOver ? "text-emerald-300" : "text-emerald-400"}`} />
        </div>
        <div>
          {fileName ? (
            <>
              <p className="text-sm font-medium text-emerald-400">{fileName}</p>
              <p className="mt-1 text-xs text-zinc-500">Click or drop to replace</p>
            </>
          ) : (
            <>
              <p className="text-sm font-medium text-zinc-300">
                Drag & drop your CSV file here
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                or click to browse. Max 50MB.
              </p>
            </>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
      </div>

      {/* Parse error */}
      {parseError && (
        <div className="flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          {parseError}
        </div>
      )}

      {/* Preview table */}
      {preview && (
        <div className="rounded-xl border border-white/[0.06] overflow-hidden">
          <div className="flex items-center justify-between bg-white/[0.03] px-4 py-3">
            <span className="text-xs font-medium text-zinc-300">
              {fileName} — {preview.rowCount.toLocaleString()} rows detected
            </span>
            {preview.valid ? (
              <span className="flex items-center gap-1 text-xs text-emerald-400">
                <Check className="h-3.5 w-3.5" /> Valid
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-red-400">
                <AlertCircle className="h-3.5 w-3.5" /> {preview.errors.join(", ")}
              </span>
            )}
          </div>
          <div className="overflow-x-auto p-4">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/[0.06] text-zinc-500">
                  {preview.columns.map((col) => (
                    <th key={col} className="pb-2 pr-4 font-medium">{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.length === 0 ? (
                  <tr>
                    <td colSpan={preview.columns.length} className="py-8 text-center text-zinc-600">
                      No data rows found
                    </td>
                  </tr>
                ) : (
                  preview.rows.map((row, i) => (
                    <tr key={i} className="text-zinc-400">
                      {preview.columns.map((col) => (
                        <td key={col} className="py-1.5 pr-4 font-mono">
                          {String(row[col] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Step 2: Strategy selection
// ============================================================================

function StrategySelectStep() {
  const store = useBacktestStore();

  return (
    <div className="space-y-4">
      <p className="text-sm text-zinc-400">Choose a trading strategy to backtest.</p>
      {(Object.keys(STRATEGY_META) as StrategyType[]).map((key) => {
        const meta = STRATEGY_META[key];
        const isSelected = store.strategyType === key;
        return (
          <button
            key={key}
            onClick={() => store.setStrategyType(key)}
            className={`flex w-full items-start gap-4 rounded-xl border p-4 text-left transition-all ${
              isSelected
                ? "border-emerald-500/50 bg-emerald-500/[0.06] ring-1 ring-emerald-500/30"
                : "border-white/[0.06] bg-[#0f0f0f] hover:border-white/[0.12]"
            }`}
          >
            <div
              className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl ${
                isSelected
                  ? "bg-emerald-500/20 text-emerald-400"
                  : "bg-white/[0.04] text-zinc-500"
              }`}
            >
              <meta.icon className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-white">
                  {meta.title}
                </span>
                {isSelected && (
                  <span className="rounded-full bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400">
                    Selected
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-zinc-500">{meta.desc}</p>
            </div>
            <div
              className={`mt-2 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border ${
                isSelected
                  ? "border-emerald-500 bg-emerald-500"
                  : "border-white/[0.15]"
              }`}
            >
              {isSelected && <Check className="h-3 w-3 text-black" />}
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ============================================================================
// Step 3: Strategy parameters
// ============================================================================

function StrategyParamsStep() {
  const store = useBacktestStore();
  const params = store.strategyParams;
  const setParams = store.setStrategyParams;

  return (
    <div className="space-y-6">
      {store.strategyType === "ma_cross" && (
        <>
          <SliderField
            label="Fast Period"
            value={params.fastPeriod}
            min={2}
            max={50}
            onChange={(v) => setParams({ fastPeriod: v })}
            hint="Shorter moving average window"
          />
          <SliderField
            label="Slow Period"
            value={params.slowPeriod}
            min={5}
            max={200}
            onChange={(v) => setParams({ slowPeriod: v })}
            hint="Longer moving average window"
          />
          <ToggleField
            label="MA Type"
            options={[
              { value: "sma", label: "SMA" },
              { value: "ema", label: "EMA" },
            ]}
            value={params.maType}
            onChange={(v) => setParams({ maType: v as "sma" | "ema" })}
          />
        </>
      )}

      {store.strategyType === "rsi" && (
        <>
          <SliderField
            label="RSI Period"
            value={params.rsiPeriod}
            min={2}
            max={30}
            onChange={(v) => setParams({ rsiPeriod: v })}
            hint="Lookback period for RSI calculation"
          />
          <SliderField
            label="Oversold Level"
            value={params.oversold}
            min={10}
            max={40}
            onChange={(v) => setParams({ oversold: v })}
            hint="Buy when RSI drops below this level"
          />
          <SliderField
            label="Overbought Level"
            value={params.overbought}
            min={60}
            max={90}
            onChange={(v) => setParams({ overbought: v })}
            hint="Sell when RSI rises above this level"
          />
        </>
      )}

      {store.strategyType === "bollinger" && (
        <>
          <SliderField
            label="Period"
            value={params.bbPeriod}
            min={5}
            max={50}
            onChange={(v) => setParams({ bbPeriod: v })}
            hint="Moving average lookback period"
          />
          <SliderField
            label="Std Dev Multiplier"
            value={params.bbStd}
            min={1.0}
            max={3.0}
            step={0.1}
            onChange={(v) => setParams({ bbStd: v })}
            hint="Band width. 2.0 = 95% of prices within bands"
          />
        </>
      )}
    </div>
  );
}

function SliderField({
  label,
  value,
  min,
  max,
  step = 1,
  hint,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  hint?: string;
  onChange: (v: number) => void;
}) {
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <label className="text-sm font-medium text-zinc-400">{label}</label>
        <span className="text-sm font-bold text-white tabular-nums">
          {step < 1 ? value.toFixed(1) : value}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-white/[0.08] accent-emerald-500 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-emerald-500 [&::-webkit-slider-thumb]:shadow-lg"
        style={{
          background: `linear-gradient(to right, #10b981 0%, #10b981 ${pct}%, rgba(255,255,255,0.08) ${pct}%)`,
        }}
      />
      {hint && (
        <p className="mt-1 text-[11px] text-zinc-600">{hint}</p>
      )}
    </div>
  );
}

function ToggleField({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-zinc-400">
        {label}
      </label>
      <div className="flex rounded-xl bg-white/[0.04] p-1">
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onChange(opt.value)}
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition-all ${
              value === opt.value
                ? "bg-white/[0.08] text-white shadow-sm"
                : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Step 4: Run settings
// ============================================================================

function RunSettingsStep() {
  const store = useBacktestStore();
  const settings = store.runSettings;
  const setSettings = store.setRunSettings;
  const limit = store.dailyLimitRemaining;

  return (
    <div className="space-y-5">
      <div>
        <label className="mb-1.5 block text-sm font-medium text-zinc-400">
          Initial Capital ($)
        </label>
        <input
          type="number"
          min={100}
          step={1000}
          value={settings.initialCapital}
          onChange={(e) =>
            setSettings({ initialCapital: Number(e.target.value) || 0 })
          }
          className="w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] px-4 py-2.5 text-sm text-white outline-none transition-all focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30"
        />
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-zinc-400">
          Commission (%)
        </label>
        <input
          type="number"
          min={0}
          max={5}
          step={0.01}
          value={(settings.commission * 100).toFixed(2)}
          onChange={(e) =>
            setSettings({ commission: (Number(e.target.value) || 0) / 100 })
          }
          className="w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] px-4 py-2.5 text-sm text-white outline-none transition-all focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30"
        />
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-zinc-400">
          Backtest Name{" "}
          <span className="text-zinc-600">(optional)</span>
        </label>
        <input
          type="text"
          value={settings.backtestName}
          onChange={(e) => setSettings({ backtestName: e.target.value })}
          placeholder="e.g., AAPL MA Cross Q1 2024"
          className="w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] px-4 py-2.5 text-sm text-white placeholder-zinc-600 outline-none transition-all focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30"
        />
      </div>

      {/* Daily limit */}
      <div className="flex items-center gap-2 rounded-xl bg-white/[0.03] px-4 py-3">
        <FileText className="h-4 w-4 text-zinc-500" />
        <span className="text-xs text-zinc-400">
          Free tier:{" "}
          <span className="font-semibold text-white">{limit} backtests</span>{" "}
          remaining today
        </span>
      </div>

      {/* Summary */}
      <div className="rounded-xl border border-white/[0.06] bg-[#0f0f0f] p-4">
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">
          Configuration Summary
        </h4>
        <div className="space-y-1.5 text-xs">
          <Row label="Data" value={summaryData(store)} />
          <Row label="Strategy" value={STRATEGY_META[store.strategyType].title} />
          <Row label="Capital" value={`$${settings.initialCapital.toLocaleString()}`} />
          <Row
            label="Commission"
            value={`${(settings.commission * 100).toFixed(2)}%`}
          />
          {settings.backtestName && (
            <Row label="Name" value={settings.backtestName} />
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-zinc-500">{label}</span>
      <span className="font-medium text-zinc-200">{value}</span>
    </div>
  );
}

function summaryData(store: ReturnType<typeof useBacktestStore.getState>) {
  if (store.dataSource === "csv") return "CSV Upload";
  return store.ticker.symbol || "(none)";
}

// ============================================================================
// Preview panel (right side)
// ============================================================================

function PreviewPanel() {
  const store = useBacktestStore();

  return (
    <div className="sticky top-24">
      <div className="rounded-2xl border border-white/[0.06] bg-[#0f0f0f] p-6">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-300">Preview</h3>
          {store.isRunning && (
            <span className="flex items-center gap-1.5 text-xs text-emerald-400">
              <Loader2 className="h-3 w-3 animate-spin" />
              Running...
            </span>
          )}
        </div>

        {/* Demo chart */}
        <div className="mb-6">
          <div className="mb-2 flex items-center gap-2">
            <span className="rounded bg-white/[0.04] px-2 py-0.5 text-[11px] font-medium text-zinc-400">
              {store.dataSource === "ticker"
                ? store.ticker.symbol || "AAPL"
                : "CSV Data"}
            </span>
            <span className="text-[11px] text-zinc-600">
              {STRATEGY_META[store.strategyType].title}
            </span>
          </div>
          <DemoChart />
        </div>

        {/* Projected metrics */}
        <div>
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-600">
            What you&apos;ll get
          </h4>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Sharpe Ratio", icon: "α" },
              { label: "Sortino Ratio", icon: "σ" },
              { label: "Max Drawdown", icon: "↓" },
              { label: "Win Rate", icon: "%" },
              { label: "Profit Factor", icon: "P" },
              { label: "Total Trades", icon: "#" },
            ].map((m) => (
              <div
                key={m.label}
                className="flex items-center gap-2 rounded-lg bg-white/[0.03] px-3 py-2.5"
              >
                <span className="flex h-5 w-5 items-center justify-center rounded bg-emerald-500/10 text-[10px] font-bold text-emerald-400">
                  {m.icon}
                </span>
                <span className="text-xs text-zinc-400">{m.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function DemoChart() {
  const points = useMemo(() => {
    const pts: string[] = [];
    let v = 100;
    for (let i = 0; i < 80; i++) {
      v *= 1 + (Math.sin(i * 0.15) * 0.01 + 0.0008);
      pts.push(`${i},${(100 - v * 0.3).toFixed(1)}`);
    }
    return pts;
  }, []);

  return (
    <div className="relative h-48 rounded-xl bg-[#0a0a0a] border border-white/[0.04] p-1">
      <svg viewBox="0 0 80 60" className="h-full w-full" preserveAspectRatio="none">
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
          </linearGradient>
        </defs>
        {/* Area fill */}
        <polygon
          fill="url(#areaGrad)"
          points={`0,60 ${points.join(" ")} 80,60`}
        />
        {/* Line */}
        <polyline
          fill="none"
          stroke="#10b981"
          strokeWidth="0.8"
          points={points.join(" ")}
        />
      </svg>
    </div>
  );
}

// ============================================================================
// Page
// ============================================================================

export default function BacktestPage() {
  const router = useRouter();
  const store = useBacktestStore();

  const handleRun = useCallback(async () => {
    store.setIsRunning(true);
    try {
      const body = new FormData();
      body.append("strategy_type", store.strategyType);
      body.append("strategy_params", JSON.stringify(store.strategyParams));
      body.append("initial_capital", String(store.runSettings.initialCapital));
      body.append("commission", String(store.runSettings.commission));
      body.append("name", store.runSettings.backtestName || "");

      if (store.dataSource === "ticker") {
        body.append("ticker", store.ticker.symbol);
        body.append("start_date", store.ticker.startDate);
        body.append("end_date", store.ticker.endDate);
      }
      // CSV upload goes here when backend supports it

      const res = await fetch(
        `${API_URL}/backtest/run`,
        { method: "POST", body },
      );

      if (res.ok) {
        const data = await res.json();
        const id = data.data?.id ?? data.id;
        router.push(`/results/${id}`);
      }
    } catch (err) {
      console.error("Backtest failed", err);
    } finally {
      store.setIsRunning(false);
    }
  }, [store, router]);

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/dashboard"
          className="mb-3 inline-flex items-center gap-1 text-xs text-zinc-500 transition-colors hover:text-zinc-300"
        >
          <ArrowLeft className="h-3 w-3" /> Dashboard
        </Link>
        <h1 className="text-2xl font-bold text-white">New Backtest</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Configure your strategy in 4 steps and run a backtest.
        </p>
      </div>

      {/* Step indicator */}
      <div className="mb-10">
        <StepIndicator current={store.currentStep} />
      </div>

      {/* Two-column layout */}
      <div className="grid gap-10 lg:grid-cols-[1fr_460px]">
        {/* Left: Configuration */}
        <div className="min-w-0">
          <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-6">
            <h2 className="mb-6 text-lg font-semibold text-white">
              {STEPS[store.currentStep - 1].label}
            </h2>

            {store.currentStep === 1 && <DataSourceStep />}
            {store.currentStep === 2 && <StrategySelectStep />}
            {store.currentStep === 3 && <StrategyParamsStep />}
            {store.currentStep === 4 && <RunSettingsStep />}

            {/* Navigation buttons */}
            <div className="mt-8 flex items-center justify-between border-t border-white/[0.04] pt-6">
              <button
                onClick={store.prevStep}
                disabled={store.currentStep === 1}
                className="flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-zinc-400 transition-all hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-4 w-4" />
                Back
              </button>

              {store.currentStep < 4 ? (
                <button
                  onClick={store.nextStep}
                  className="flex items-center gap-1.5 rounded-xl bg-white px-5 py-2.5 text-sm font-semibold text-black transition-all hover:bg-zinc-200"
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  onClick={handleRun}
                  disabled={store.isRunning || store.dailyLimitRemaining <= 0}
                  className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-400 px-8 py-3 text-sm font-semibold text-black shadow-lg shadow-emerald-500/25 transition-all hover:from-emerald-400 hover:to-emerald-300 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {store.isRunning ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Running Backtest...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 fill-black" />
                      Run Backtest
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Right: Preview */}
        <PreviewPanel />
      </div>
    </div>
  );
}
