"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface DrawdownChartProps {
  data: Array<{ date: string; drawdown: number }>;
}

export function DrawdownChart({ data }: DrawdownChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-surface-400">
        No drawdown data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 12, fill: "#94a3b8" }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          tick={{ fontSize: 12, fill: "#94a3b8" }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
          domain={["auto", 0]}
        />
        <Tooltip
          contentStyle={{
            borderRadius: "8px",
            border: "1px solid #e2e8f0",
          }}
          formatter={(value: number) => [
            `${(value * 100).toFixed(2)}%`,
            "Drawdown",
          ]}
        />
        <Area
          type="monotone"
          dataKey="drawdown"
          stroke="#ef4444"
          fill="#fecaca"
          strokeWidth={1}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
