"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Play, Loader2 } from "lucide-react";

interface StrategyFormProps {
  onSubmit: (params: StrategyParams) => Promise<void>;
}

export interface StrategyParams {
  symbol: string;
  strategy: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  fast_window?: number;
  slow_window?: number;
  rsi_period?: number;
}

const STRATEGIES = [
  { value: "sma_cross", label: "SMA Crossover" },
  { value: "rsi_mean_reversion", label: "RSI Mean Reversion" },
  { value: "bollinger_breakout", label: "Bollinger Breakout" },
  { value: "macd", label: "MACD Signal" },
];

export function StrategyForm({ onSubmit }: StrategyFormProps) {
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    const form = new FormData(e.currentTarget);
    try {
      await onSubmit({
        symbol: form.get("symbol") as string,
        strategy: form.get("strategy") as string,
        start_date: form.get("start_date") as string,
        end_date: form.get("end_date") as string,
        initial_capital: Number(form.get("initial_capital")),
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <Card>
        <CardHeader>
          <CardTitle>Strategy Configuration</CardTitle>
        </CardHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">
              Symbol
            </label>
            <Input name="symbol" required placeholder="AAPL" />
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">
              Strategy
            </label>
            <select
              name="strategy"
              required
              className="w-full px-3 py-2 rounded-lg border border-surface-300 bg-white text-surface-900 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              defaultValue=""
            >
              <option value="" disabled>
                Select...
              </option>
              {STRATEGIES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">
              Start Date
            </label>
            <Input type="date" name="start_date" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">
              End Date
            </label>
            <Input type="date" name="end_date" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-surface-700 mb-1">
              Initial Capital ($)
            </label>
            <Input
              type="number"
              name="initial_capital"
              required
              min={1000}
              defaultValue={10000}
            />
          </div>
        </div>
        <div className="mt-6">
          <Button type="submit" disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run Backtest
              </>
            )}
          </Button>
        </div>
      </Card>
    </form>
  );
}
