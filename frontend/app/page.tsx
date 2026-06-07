import type { Metadata } from "next";
import Link from "next/link";
import {
  AnimateSection,
  AnimateItem,
  AnimateStagger,
} from "@/components/landing/animate-section";

// ============================================================================
// SEO Metadata
// ============================================================================

export const metadata: Metadata = {
  title: "QuantFlow — Backtest Any Trading Strategy in 5 Minutes",
  description:
    "Professional quantitative backtesting platform. Upload CSV or enter a ticker, pick a strategy, and get Sharpe ratio, drawdown, win rate analysis instantly. No coding required.",
  keywords: [
    "backtesting",
    "trading strategy",
    "quantitative analysis",
    "algo trading",
    "Sharpe ratio",
    "stock backtest",
    "RSI",
    "MACD",
    "Bollinger Bands",
  ],
  openGraph: {
    title: "QuantFlow — Backtest Any Trading Strategy in 5 Minutes",
    description:
      "Professional quantitative backtesting. No coding required. Instant results.",
    type: "website",
    siteName: "QuantFlow",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "QuantFlow — Backtest Any Strategy in 5 Minutes",
    description:
      "Professional quantitative backtesting. No coding required. Instant results.",
  },
};

// ============================================================================
// Constants
// ============================================================================

const STRATEGIES = [
  {
    title: "MA Crossover",
    tag: "Trend Following",
    description:
      "Buy when the fast moving average crosses above the slow one. Sell when it crosses below. Classic trend-following strategy that captures major market moves.",
    params: [
      { label: "Fast Period", value: "10" },
      { label: "Slow Period", value: "30" },
      { label: "MA Type", value: "SMA / EMA" },
    ],
    color: "from-emerald-500 to-teal-600",
  },
  {
    title: "RSI Strategy",
    tag: "Mean Reversion",
    description:
      "Buy when RSI indicates oversold conditions (below 30). Sell when overbought (above 70). Mean-reversion strategy for range-bound markets.",
    params: [
      { label: "RSI Period", value: "14" },
      { label: "Oversold", value: "30" },
      { label: "Overbought", value: "70" },
    ],
    color: "from-violet-500 to-purple-600",
  },
  {
    title: "Bollinger Bands",
    tag: "Volatility Breakout",
    description:
      "Buy when price touches the lower Bollinger Band. Sell at the upper band. Captures mean-reversion within volatility envelopes.",
    params: [
      { label: "Period", value: "20" },
      { label: "Std Dev", value: "2.0" },
      { label: "Band Width", value: "Auto" },
    ],
    color: "from-amber-500 to-orange-600",
  },
];

const PLANS = [
  {
    name: "Free",
    price: "$0",
    period: "",
    cta: "Get Started",
    href: "/register",
    features: [
      "5 backtests per day",
      "US equities & major ETFs",
      "3 built-in strategies",
      "CSV upload support",
      "Basic metrics & charts",
      "Community support",
    ],
  },
  {
    name: "Pro",
    price: "$19",
    period: "/month",
    cta: "Start Free Trial",
    href: "/register",
    featured: true,
    features: [
      "Unlimited backtests",
      "Global markets & crypto",
      "All strategies + custom params",
      "Yahoo Finance integration",
      "Advanced metrics (Sortino, VaR)",
      "Walk-forward analysis",
      "Priority email support",
    ],
  },
  {
    name: "Quant",
    price: "$49",
    period: "/month",
    cta: "Contact Sales",
    href: "/register",
    features: [
      "Everything in Pro",
      "Custom strategy scripting",
      "Multi-asset portfolios",
      "API access",
      "Data export (CSV, JSON, PDF)",
      "Dedicated infrastructure",
      "SLA guarantee",
    ],
  },
];

const VALUE_PROPS = [
  {
    icon: (
      <svg className="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 6v6l4 2" />
      </svg>
    ),
    title: "Instant Results",
    description:
      "Run backtests in seconds, not hours. Our vectorized engine processes 10 years of daily data in under 1 second.",
  },
  {
    icon: (
      <svg className="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M3 3v18h18" />
        <path d="M7 16l4-4 4 4 5-6" />
      </svg>
    ),
    title: "Professional Metrics",
    description:
      "Sharpe ratio, Sortino, max drawdown, win rate, profit factor — every metric institutional quants rely on.",
  },
  {
    icon: (
      <svg className="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>
    ),
    title: "No Code Required",
    description:
      "Upload a CSV or enter a ticker symbol. No Python, no SQL, no infrastructure — just results.",
  },
];

const FOOTER_LINKS = {
  Product: ["Features", "Pricing", "Strategies", "API"],
  Company: ["About", "Blog", "Careers", "Contact"],
  Legal: ["Privacy Policy", "Terms of Service", "Disclaimer"],
};

// ============================================================================
// Components
// ============================================================================

function Header() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-white/[0.06] bg-[#0a0a0a]/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-xl font-bold tracking-tight text-white">
            Quant<span className="text-emerald-400">Flow</span>
          </span>
        </Link>
        <nav className="hidden items-center gap-6 md:flex">
          <a href="#features" className="text-sm text-zinc-400 transition-colors hover:text-white">
            Features
          </a>
          <a href="#strategies" className="text-sm text-zinc-400 transition-colors hover:text-white">
            Strategies
          </a>
          <a href="#pricing" className="text-sm text-zinc-400 transition-colors hover:text-white">
            Pricing
          </a>
          <a href="#demo" className="text-sm text-zinc-400 transition-colors hover:text-white">
            Demo
          </a>
        </nav>
        <div className="flex items-center gap-3">
          <Link
            href="/login"
            className="hidden text-sm text-zinc-400 transition-colors hover:text-white sm:inline"
          >
            Sign In
          </Link>
          <Link
            href="/register"
            className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-black transition-all hover:bg-emerald-400"
          >
            Get Started
          </Link>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden pt-32 pb-20 sm:pt-40 sm:pb-28">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-[#0a0a0a]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(16,185,129,0.12),transparent)]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_80%_50%,rgba(139,92,246,0.08),transparent)]" />

      <div className="relative mx-auto max-w-7xl px-6">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          {/* Left — text */}
          <div>
            <AnimateStagger>
              <AnimateItem>
                <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-4 py-1.5">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                  </span>
                  <span className="text-xs font-medium text-emerald-400">
                    Now in Public Beta
                  </span>
                </div>
              </AnimateItem>

              <AnimateItem>
                <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-6xl">
                  Backtest Any{" "}
                  <span className="bg-gradient-to-r from-emerald-400 to-emerald-200 bg-clip-text text-transparent">
                    Trading Strategy
                  </span>
                  <br />
                  in 5 Minutes
                </h1>
              </AnimateItem>

              <AnimateItem>
                <p className="mt-6 max-w-xl text-lg leading-relaxed text-zinc-400 sm:text-xl">
                  No coding required. Upload your data or enter a ticker, pick a
                  strategy, and get professional-grade analysis instantly.
                </p>
              </AnimateItem>

              <AnimateItem>
                <div className="mt-8 flex flex-col gap-4 sm:flex-row">
                  <Link
                    href="/register"
                    className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-400 px-8 py-3.5 text-base font-semibold text-black shadow-lg shadow-emerald-500/25 transition-all hover:from-emerald-400 hover:to-emerald-300 hover:shadow-emerald-500/40"
                  >
                    Start for Free
                    <svg className="ml-2 h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clipRule="evenodd" />
                    </svg>
                  </Link>
                  <a
                    href="#demo"
                    className="inline-flex items-center justify-center rounded-xl border border-zinc-700 px-8 py-3.5 text-base font-medium text-zinc-300 transition-all hover:border-zinc-500 hover:text-white"
                  >
                    See Demo
                  </a>
                </div>
              </AnimateItem>

              <AnimateItem>
                <div className="mt-8 flex items-center gap-6 text-sm text-zinc-500">
                  <span className="flex items-center gap-1.5">
                    <svg className="h-4 w-4 text-emerald-500" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                    </svg>
                    No credit card
                  </span>
                  <span className="flex items-center gap-1.5">
                    <svg className="h-4 w-4 text-emerald-500" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                    </svg>
                    5 free backtests / day
                  </span>
                </div>
              </AnimateItem>
            </AnimateStagger>
          </div>

          {/* Right — dashboard preview */}
          <AnimateItem className="hidden lg:block">
            <div className="relative">
              <div className="rounded-xl border border-white/[0.08] bg-[#0f0f0f] p-4 shadow-2xl">
                {/* Mock chart header */}
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-xs font-medium text-emerald-400">
                      AAPL
                    </span>
                    <span className="text-xs text-zinc-500">MA Crossover</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
                    <span className="text-xs text-zinc-500">Running</span>
                  </div>
                </div>
                {/* Mock chart body */}
                <div className="mb-4 flex items-end gap-1">
                  {Array.from({ length: 40 }).map((_, i) => {
                    const h = 20 + Math.sin(i * 0.3) * 30 + Math.random() * 40;
                    return (
                      <div
                        key={i}
                        className="flex-1 rounded-sm bg-gradient-to-t from-emerald-500/30 to-emerald-500/10"
                        style={{ height: `${h}px` }}
                      />
                    );
                  })}
                </div>
                {/* Mock metrics */}
                <div className="grid grid-cols-4 gap-3">
                  {[
                    { label: "Sharpe", value: "1.82", color: "text-white" },
                    { label: "Return", value: "+32.4%", color: "text-emerald-400" },
                    { label: "Max DD", value: "-12.1%", color: "text-red-400" },
                    { label: "Trades", value: "47", color: "text-zinc-300" },
                  ].map((m) => (
                    <div key={m.label} className="rounded-lg bg-white/[0.03] p-3 text-center">
                      <div className="text-[10px] text-zinc-500">{m.label}</div>
                      <div className={`mt-1 text-sm font-bold ${m.color}`}>{m.value}</div>
                    </div>
                  ))}
                </div>
              </div>
              {/* Glow behind the card */}
              <div className="absolute inset-0 -z-10 translate-y-4 scale-95 rounded-xl bg-gradient-to-r from-emerald-500/20 to-violet-500/20 blur-2xl" />
            </div>
          </AnimateItem>
        </div>
      </div>
    </section>
  );
}

function ValueProps() {
  return (
    <AnimateSection id="features" className="bg-[#0a0a0a] py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6">
        <AnimateItem>
          <h2 className="text-center text-3xl font-bold text-white sm:text-4xl">
            Everything you need to{" "}
            <span className="text-emerald-400">backtest</span>
          </h2>
        </AnimateItem>
        <AnimateItem>
          <p className="mx-auto mt-4 max-w-2xl text-center text-zinc-400">
            Professional-grade quantitative analysis, simplified.
          </p>
        </AnimateItem>

        <AnimateStagger className="mt-16 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {VALUE_PROPS.map((prop) => (
            <AnimateItem key={prop.title}>
              <div className="group rounded-2xl border border-white/[0.06] bg-[#111] p-8 transition-all hover:border-white/[0.12] hover:bg-[#161616]">
                <div className="mb-4 inline-flex rounded-xl bg-emerald-500/10 p-3 text-emerald-400">
                  {prop.icon}
                </div>
                <h3 className="text-lg font-semibold text-white">{prop.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-zinc-400">
                  {prop.description}
                </p>
              </div>
            </AnimateItem>
          ))}
        </AnimateStagger>
      </div>
    </AnimateSection>
  );
}

function Strategies() {
  return (
    <AnimateSection
      id="strategies"
      className="border-t border-white/[0.04] bg-[#0c0c0c] py-24 sm:py-32"
    >
      <div className="mx-auto max-w-7xl px-6">
        <AnimateItem>
          <h2 className="text-center text-3xl font-bold text-white sm:text-4xl">
            Built-in Strategies,{" "}
            <span className="text-emerald-400">Ready to Use</span>
          </h2>
        </AnimateItem>
        <AnimateItem>
          <p className="mx-auto mt-4 max-w-2xl text-center text-zinc-400">
            Three battle-tested strategies with configurable parameters. No
            coding needed to start.
          </p>
        </AnimateItem>

        <AnimateStagger className="mt-16 grid gap-8 lg:grid-cols-3">
          {STRATEGIES.map((s) => (
            <AnimateItem key={s.title}>
              <div className="group relative overflow-hidden rounded-2xl border border-white/[0.06] bg-[#111] transition-all hover:border-white/[0.12]">
                {/* Gradient top bar */}
                <div className={`h-1.5 w-full bg-gradient-to-r ${s.color}`} />
                <div className="p-8">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-white">{s.title}</h3>
                    <span className="rounded-full bg-white/[0.05] px-2.5 py-0.5 text-[11px] font-medium text-zinc-400">
                      {s.tag}
                    </span>
                  </div>
                  <p className="mt-4 text-sm leading-relaxed text-zinc-400">
                    {s.description}
                  </p>
                  <div className="mt-6 space-y-2">
                    <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                      Parameters
                    </p>
                    {s.params.map((p) => (
                      <div
                        key={p.label}
                        className="flex items-center justify-between rounded-lg bg-white/[0.03] px-3 py-2 text-sm"
                      >
                        <span className="text-zinc-400">{p.label}</span>
                        <span className="font-mono text-zinc-200">{p.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </AnimateItem>
          ))}
        </AnimateStagger>
      </div>
    </AnimateSection>
  );
}

function Pricing() {
  return (
    <AnimateSection
      id="pricing"
      className="border-t border-white/[0.04] bg-[#0a0a0a] py-24 sm:py-32"
    >
      <div className="mx-auto max-w-7xl px-6">
        <AnimateItem>
          <h2 className="text-center text-3xl font-bold text-white sm:text-4xl">
            Simple,{" "}
            <span className="text-emerald-400">Transparent Pricing</span>
          </h2>
        </AnimateItem>
        <AnimateItem>
          <p className="mx-auto mt-4 max-w-2xl text-center text-zinc-400">
            Start free. Upgrade when you need more power.
          </p>
        </AnimateItem>

        <AnimateStagger className="mx-auto mt-16 grid max-w-5xl gap-8 lg:grid-cols-3">
          {PLANS.map((plan) => (
            <AnimateItem key={plan.name}>
              <div
                className={`relative flex h-full flex-col rounded-2xl border bg-[#111] p-8 transition-all hover:border-white/[0.12] ${
                  plan.featured
                    ? "border-emerald-500/40 shadow-lg shadow-emerald-500/5"
                    : "border-white/[0.06]"
                }`}
              >
                {plan.featured && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="rounded-full bg-emerald-500 px-3.5 py-1 text-xs font-semibold text-black">
                      Most Popular
                    </span>
                  </div>
                )}
                <div>
                  <h3 className="text-xl font-semibold text-white">{plan.name}</h3>
                  <div className="mt-4 flex items-baseline gap-1">
                    <span className="text-4xl font-bold text-white">{plan.price}</span>
                    {plan.period && (
                      <span className="text-zinc-500">{plan.period}</span>
                    )}
                  </div>
                </div>
                <ul className="mt-8 flex-1 space-y-3">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-3 text-sm">
                      <svg
                        className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-500"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
                          clipRule="evenodd"
                        />
                      </svg>
                      <span className="text-zinc-300">{f}</span>
                    </li>
                  ))}
                </ul>
                <Link
                  href={plan.href}
                  className={`mt-8 block rounded-xl py-3 text-center text-sm font-semibold transition-all ${
                    plan.featured
                      ? "bg-gradient-to-r from-emerald-500 to-emerald-400 text-black shadow-lg shadow-emerald-500/25 hover:from-emerald-400 hover:to-emerald-300"
                      : "border border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-white"
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            </AnimateItem>
          ))}
        </AnimateStagger>
      </div>
    </AnimateSection>
  );
}

function CTA() {
  return (
    <AnimateSection className="border-t border-white/[0.04] bg-[#0c0c0c] py-24 sm:py-32">
      <div className="mx-auto max-w-4xl px-6 text-center">
        <AnimateItem>
          <h2 className="text-3xl font-bold text-white sm:text-5xl">
            Start backtesting for{" "}
            <span className="bg-gradient-to-r from-emerald-400 to-emerald-200 bg-clip-text text-transparent">
              free
            </span>{" "}
            today
          </h2>
        </AnimateItem>
        <AnimateItem>
          <p className="mt-4 text-lg text-zinc-400">
            No credit card required. 5 free backtests every day.
          </p>
        </AnimateItem>
        <AnimateItem>
          <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/register"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-400 px-10 py-4 text-base font-semibold text-black shadow-lg shadow-emerald-500/25 transition-all hover:from-emerald-400 hover:to-emerald-300"
            >
              Get Started Free
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clipRule="evenodd" />
              </svg>
            </Link>
            <a
              href="#demo"
              className="inline-flex items-center rounded-xl border border-zinc-700 px-10 py-4 text-base font-medium text-zinc-300 transition-all hover:border-zinc-500 hover:text-white"
            >
              Schedule a Demo
            </a>
          </div>
        </AnimateItem>
      </div>
    </AnimateSection>
  );
}

function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-white/[0.06] bg-[#0a0a0a] py-16">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-12 sm:grid-cols-2 lg:grid-cols-5">
          {/* Brand */}
          <div className="lg:col-span-2">
            <Link href="/" className="inline-flex items-center gap-2">
              <span className="text-xl font-bold tracking-tight text-white">
                Quant<span className="text-emerald-400">Flow</span>
              </span>
            </Link>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-zinc-400">
              Professional quantitative backtesting platform. Build, test, and
              deploy algorithmic trading strategies with institutional-grade
              tools.
            </p>
            <div className="mt-6 flex items-center gap-4">
              {["Twitter", "GitHub", "LinkedIn"].map((name) => (
                <a
                  key={name}
                  href="#"
                  className="rounded-lg bg-white/[0.04] p-2 text-zinc-400 transition-colors hover:bg-white/[0.08] hover:text-white"
                  aria-label={name}
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2z" />
                  </svg>
                </a>
              ))}
            </div>
          </div>

          {/* Links */}
          {Object.entries(FOOTER_LINKS).map(([heading, links]) => (
            <div key={heading}>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                {heading}
              </h4>
              <ul className="mt-4 space-y-3">
                {links.map((label) => (
                  <li key={label}>
                    <a
                      href="#"
                      className="text-sm text-zinc-400 transition-colors hover:text-white"
                    >
                      {label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 border-t border-white/[0.04] pt-8 flex flex-col items-center justify-between gap-4 sm:flex-row">
          <p className="text-xs text-zinc-500">
            &copy; {year} QuantFlow. All rights reserved.
          </p>
          <p className="text-xs text-zinc-600">
            Trading involves risk. Past performance does not guarantee future
            results.
          </p>
        </div>
      </div>
    </footer>
  );
}

// ============================================================================
// Page
// ============================================================================

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Header />
      <main>
        <Hero />
        <ValueProps />
        <Strategies />
        <Pricing />
        <CTA />
        {/* Demo section anchor */}
        <section
          id="demo"
          className="border-t border-white/[0.04] bg-[#0c0c0c] py-24 sm:py-32"
        >
          <div className="mx-auto max-w-7xl px-6">
            <AnimateSection>
              <AnimateItem>
                <h2 className="text-center text-3xl font-bold text-white sm:text-4xl">
                  See it in <span className="text-emerald-400">action</span>
                </h2>
                <p className="mx-auto mt-4 max-w-2xl text-center text-zinc-400">
                  Watch how easy it is to run a backtest on QuantFlow.
                </p>
              </AnimateItem>
              <AnimateItem>
                <div className="mx-auto mt-12 max-w-4xl">
                  <div className="aspect-video rounded-2xl border border-white/[0.06] bg-[#111] flex items-center justify-center">
                    <div className="text-center">
                      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/10">
                        <svg
                          className="h-8 w-8 text-emerald-400"
                          viewBox="0 0 24 24"
                          fill="currentColor"
                        >
                          <path d="M8 5v14l11-7z" />
                        </svg>
                      </div>
                      <p className="text-sm text-zinc-500">
                        Demo video coming soon
                      </p>
                    </div>
                  </div>
                </div>
              </AnimateItem>
            </AnimateSection>
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
