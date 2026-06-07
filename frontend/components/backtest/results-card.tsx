import { Card } from "@/components/ui/card";
import { formatCurrency, formatPercent } from "@/lib/utils";
import { TrendingUp, TrendingDown, Activity, Target } from "lucide-react";

interface ResultsCardProps {
  totalReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
  totalTrades: number;
  finalCapital: number;
}

export function ResultsCard({
  totalReturn,
  sharpeRatio,
  maxDrawdown,
  winRate,
  totalTrades,
  finalCapital,
}: ResultsCardProps) {
  const isPositive = totalReturn >= 0;

  const metrics = [
    {
      label: "Total Return",
      value: formatPercent(totalReturn),
      icon: isPositive ? TrendingUp : TrendingDown,
      color: isPositive ? "text-green-600" : "text-red-600",
    },
    {
      label: "Sharpe Ratio",
      value: sharpeRatio.toFixed(2),
      icon: Activity,
      color: "text-surface-900",
    },
    {
      label: "Max Drawdown",
      value: formatPercent(maxDrawdown),
      icon: TrendingDown,
      color: "text-red-600",
    },
    {
      label: "Win Rate",
      value: formatPercent(winRate, 1),
      icon: Target,
      color: "text-surface-900",
    },
  ];

  return (
    <div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <div className="flex items-center justify-between">
              <span className="text-sm text-surface-500">{metric.label}</span>
              <metric.icon className={`h-4 w-4 ${metric.color}`} />
            </div>
            <p className={`mt-2 text-2xl font-bold ${metric.color}`}>
              {metric.value}
            </p>
          </Card>
        ))}
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Card>
          <span className="text-sm text-surface-500">Final Capital</span>
          <p className="mt-1 text-xl font-bold text-surface-900">
            {formatCurrency(finalCapital)}
          </p>
        </Card>
        <Card>
          <span className="text-sm text-surface-500">Total Trades</span>
          <p className="mt-1 text-xl font-bold text-surface-900">
            {totalTrades}
          </p>
        </Card>
      </div>
    </div>
  );
}
