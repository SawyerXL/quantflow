import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Shared Backtest | QuantFlow",
  description:
    "Quantitative backtesting platform. Build, test, and deploy algorithmic trading strategies with institutional-grade tools.",
  openGraph: {
    title: "Shared Backtest | QuantFlow",
    description:
      "See this backtest result powered by QuantFlow — professional quantitative analysis in minutes.",
    type: "website",
    siteName: "QuantFlow",
  },
  twitter: {
    card: "summary_large_image",
    title: "Shared Backtest | QuantFlow",
    description: "See this backtest result powered by QuantFlow.",
  },
};

export default function ShareLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
