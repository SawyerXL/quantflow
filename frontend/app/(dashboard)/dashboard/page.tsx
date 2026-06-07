import {
  BarChart3,
  TrendingUp,
  Activity,
  Clock,
  Plus,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-surface-900">Dashboard</h1>
        <Link href="/backtest" className="btn-primary flex items-center gap-2">
          <Plus className="h-4 w-4" />
          New Backtest
        </Link>
      </div>

      {/* Stats */}
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            label: "Total Backtests",
            value: "0",
            icon: BarChart3,
            change: null,
          },
          {
            label: "Win Rate",
            value: "--",
            icon: TrendingUp,
            change: null,
          },
          {
            label: "Avg Sharpe",
            value: "--",
            icon: Activity,
            change: null,
          },
          {
            label: "Running Now",
            value: "0",
            icon: Clock,
            change: null,
          },
        ].map((stat) => (
          <div key={stat.label} className="card">
            <div className="flex items-center justify-between">
              <span className="text-sm text-surface-500">{stat.label}</span>
              <stat.icon className="h-4 w-4 text-surface-400" />
            </div>
            <p className="mt-2 text-2xl font-bold text-surface-900">
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      {/* Recent Backtests */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold text-surface-900">
          Recent Backtests
        </h2>
        <div className="mt-4 card">
          <div className="py-12 text-center text-surface-400">
            <BarChart3 className="mx-auto h-12 w-12 opacity-20" />
            <p className="mt-4 text-sm">
              No backtests yet. Run your first strategy analysis.
            </p>
            <Link
              href="/backtest"
              className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:text-brand-500"
            >
              Get started <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
