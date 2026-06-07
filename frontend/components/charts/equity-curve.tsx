"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface EquityCurveProps {
  data: Array<{ date: string; equity: number }>;
}

export function EquityCurve({ data }: EquityCurveProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-surface-400">
        No equity data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data}>
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
          tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
        />
        <Tooltip
          contentStyle={{
            borderRadius: "8px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
          }}
          formatter={(value: number) => [
            `$${value.toLocaleString()}`,
            "Equity",
          ]}
        />
        <Line
          type="monotone"
          dataKey="equity"
          stroke="#2563eb"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
