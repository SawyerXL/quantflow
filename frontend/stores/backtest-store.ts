"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

// ============================================================================
// Types
// ============================================================================

export type DataSource = "csv" | "ticker";
export type StrategyType = "ma_cross" | "rsi" | "bollinger";
export type Step = 1 | 2 | 3 | 4;

export interface CSVPreview {
  columns: string[];
  rows: Array<Record<string, unknown>>;
  rowCount: number;
  valid: boolean;
  errors: string[];
}

export interface TickerState {
  symbol: string;
  startDate: string;
  endDate: string;
}

export interface StrategyParams {
  // MA Cross
  fastPeriod: number;
  slowPeriod: number;
  maType: "sma" | "ema";
  // RSI
  rsiPeriod: number;
  oversold: number;
  overbought: number;
  // Bollinger
  bbPeriod: number;
  bbStd: number;
}

export interface RunSettings {
  initialCapital: number;
  commission: number;
  backtestName: string;
}

export interface BacktestState {
  // Wizard
  currentStep: Step;
  setStep: (step: Step) => void;
  nextStep: () => void;
  prevStep: () => void;

  // Data source
  dataSource: DataSource;
  setDataSource: (source: DataSource) => void;
  csvPreview: CSVPreview | null;
  setCSVPreview: (preview: CSVPreview | null) => void;
  ticker: TickerState;
  setTicker: (ticker: Partial<TickerState>) => void;

  // Strategy
  strategyType: StrategyType;
  setStrategyType: (type: StrategyType) => void;
  strategyParams: StrategyParams;
  setStrategyParams: (params: Partial<StrategyParams>) => void;

  // Run settings
  runSettings: RunSettings;
  setRunSettings: (settings: Partial<RunSettings>) => void;

  // Execution
  isRunning: boolean;
  setIsRunning: (v: boolean) => void;
  dailyLimitRemaining: number;

  // Derived — is the form ready to submit?
  isReady: () => boolean;
}

// ============================================================================
// Defaults
// ============================================================================

const DEFAULT_PARAMS: StrategyParams = {
  fastPeriod: 10,
  slowPeriod: 30,
  maType: "sma",
  rsiPeriod: 14,
  oversold: 30,
  overbought: 70,
  bbPeriod: 20,
  bbStd: 2.0,
};

const DEFAULT_RUN_SETTINGS: RunSettings = {
  initialCapital: 10000,
  commission: 0.001,
  backtestName: "",
};

const today = () => new Date().toISOString().split("T")[0];
const yearsAgo = (n: number) => {
  const d = new Date();
  d.setFullYear(d.getFullYear() - n);
  return d.toISOString().split("T")[0];
};

// ============================================================================
// Store
// ============================================================================

export const useBacktestStore = create<BacktestState>()(
  persist(
    (set, get) => ({
      // Wizard
      currentStep: 1,
      setStep: (step) => set({ currentStep: step }),
      nextStep: () => set((s) => ({ currentStep: Math.min(4, s.currentStep + 1) as Step })),
      prevStep: () => set((s) => ({ currentStep: Math.max(1, s.currentStep - 1) as Step })),

      // Data source
      dataSource: "ticker",
      setDataSource: (source) => set({ dataSource: source }),
      csvPreview: null,
      setCSVPreview: (preview) => set({ csvPreview: preview }),
      ticker: {
        symbol: "",
        startDate: yearsAgo(1),
        endDate: today(),
      },
      setTicker: (partial) =>
        set((s) => ({ ticker: { ...s.ticker, ...partial } })),

      // Strategy
      strategyType: "ma_cross",
      setStrategyType: (type) => set({ strategyType: type }),
      strategyParams: { ...DEFAULT_PARAMS },
      setStrategyParams: (partial) =>
        set((s) => ({ strategyParams: { ...s.strategyParams, ...partial } })),

      // Run settings
      runSettings: { ...DEFAULT_RUN_SETTINGS },
      setRunSettings: (partial) =>
        set((s) => ({ runSettings: { ...s.runSettings, ...partial } })),

      // Execution
      isRunning: false,
      setIsRunning: (v) => set({ isRunning: v }),
      dailyLimitRemaining: 5, // TODO: fetch from backend /me

      // Derived
      isReady: () => {
        const st = get();
        const hasData =
          st.dataSource === "csv"
            ? st.csvPreview !== null && st.csvPreview.valid
            : st.ticker.symbol.length > 0;
        return hasData && st.strategyType !== undefined;
      },
    }),
    {
      name: "quantflow-backtest",
      partialize: (state) => ({
        dataSource: state.dataSource,
        ticker: state.ticker,
        strategyType: state.strategyType,
        strategyParams: state.strategyParams,
        runSettings: state.runSettings,
      }),
    },
  ),
);
