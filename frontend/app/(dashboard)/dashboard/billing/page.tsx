"use client";

export const dynamic = "force-dynamic";

import { Suspense, useCallback, useEffect, useState } from "react";
import { API_URL } from "@/lib/api";
import { useSearchParams } from "next/navigation";
import {
  Check,
  Loader2,
  ExternalLink,
  Zap,
  Crown,
  Sparkles,
  Clock,
  Shield,
  RefreshCw,
} from "lucide-react";

// ============================================================================
// Types
// ============================================================================

interface SubscriptionInfo {
  plan: "free" | "pro" | "quant";
  plan_name: string;
  status: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  limits: {
    backtests_per_day: number;
    api_access: boolean;
    export_pdf?: boolean;
    custom_strategies?: boolean;
  };
  prices?: { monthly: number; yearly: number };
}

interface PlanCard {
  id: string;
  name: string;
  icon: typeof Sparkles;
  monthlyPrice: number;
  yearlyPrice: number;
  features: string[];
  cta: string;
  popular: boolean;
}

const PLANS: PlanCard[] = [
  {
    id: "free",
    name: "Free",
    icon: Zap,
    monthlyPrice: 0,
    yearlyPrice: 0,
    features: [
      "5 backtests per day",
      "US equities & ETFs",
      "3 built-in strategies",
      "CSV upload support",
      "Basic metrics & charts",
      "Community support",
    ],
    cta: "Current Plan",
    popular: false,
  },
  {
    id: "pro",
    name: "Pro",
    icon: Crown,
    monthlyPrice: 19,
    yearlyPrice: 159,
    features: [
      "Unlimited backtests",
      "Global markets & crypto",
      "All strategies + custom params",
      "Yahoo Finance integration",
      "Advanced metrics",
      "Walk-forward analysis",
      "PDF export",
      "Priority email support",
    ],
    cta: "Upgrade to Pro",
    popular: true,
  },
  {
    id: "quant",
    name: "Quant",
    icon: Sparkles,
    monthlyPrice: 49,
    yearlyPrice: 399,
    features: [
      "Everything in Pro",
      "Custom strategy scripting",
      "Multi-asset portfolios",
      "API access",
      "Data export (CSV/JSON/PDF)",
      "Dedicated infrastructure",
      "SLA guarantee",
      "Team accounts",
    ],
    cta: "Upgrade to Quant",
    popular: false,
  },
];

// ============================================================================
// Components
// ============================================================================

function Spinner() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
    </div>
  );
}

function StatusBadge({ status }: { status: string | null }) {
  if (!status || status === "inactive") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-white/[0.04] px-3 py-1 text-xs font-medium text-zinc-500">
        Inactive
      </span>
    );
  }
  if (status === "active" || status === "trialing") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-medium text-emerald-400">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
        </span>
        Active
      </span>
    );
  }
  if (status === "past_due") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-3 py-1 text-xs font-medium text-amber-400">
        <Clock className="h-3 w-3" />
        Past Due
      </span>
    );
  }
  return (
    <span className="rounded-full bg-white/[0.04] px-3 py-1 text-xs font-medium text-zinc-500">
      {status}
    </span>
  );
}

function Toast({
  message,
  type,
  onClose,
}: {
  message: string;
  type: "success" | "error";
  onClose: () => void;
}) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000);
    return () => clearTimeout(t);
  }, [onClose]);

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 rounded-xl px-5 py-3.5 text-sm font-medium shadow-2xl backdrop-blur-xl ${
        type === "success"
          ? "border border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
          : "border border-red-500/30 bg-red-500/10 text-red-400"
      }`}
    >
      {message}
    </div>
  );
}

// ============================================================================
// Page
// ============================================================================

function BillingPageInner() {
  const searchParams = useSearchParams();
  const [sub, setSub] = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [isYearly, setIsYearly] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);
  const [toast, setToast] = useState<{
    message: string;
    type: "success" | "error";
  } | null>(null);

  // Fetch subscription
  const fetchSub = useCallback(async () => {
    try {
      const res = await fetch(
        `${API_URL}/billing/subscription`,
        { headers: { Authorization: `Bearer ${localStorage.getItem("token")}` } },
      );
      if (res.ok) {
        const json = await res.json();
        setSub(json.data ?? json);
      }
    } catch (err) {
      console.error("Failed to load subscription", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSub();
  }, [fetchSub]);

  // Toast on checkout status
  useEffect(() => {
    const status = searchParams.get("checkout");
    if (status === "success") {
      setToast({ message: "Subscription activated! Welcome aboard.", type: "success" });
      fetchSub();
    } else if (status === "cancelled") {
      setToast({ message: "Checkout was cancelled. No charges were made.", type: "error" });
    }
  }, [searchParams, fetchSub]);

  // Actions
  const handleCheckout = async (planId: string) => {
    setCheckoutLoading(planId);
    try {
      const period = isYearly ? "yearly" : "monthly";
      const res = await fetch(
        `${API_URL}/billing/checkout`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
          body: JSON.stringify({ plan: planId, billing_period: period }),
        },
      );
      if (res.ok) {
        const json = await res.json();
        const data = json.data ?? json;
        window.location.href = data.checkout_url;
      } else {
        setToast({ message: "Failed to start checkout. Please try again.", type: "error" });
      }
    } catch {
      setToast({ message: "Network error. Please check your connection.", type: "error" });
    } finally {
      setCheckoutLoading(null);
    }
  };

  const handlePortal = async () => {
    setPortalLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/billing/portal`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        },
      );
      if (res.ok) {
        const json = await res.json();
        const data = json.data ?? json;
        window.location.href = data.portal_url;
      }
    } catch {
      setToast({ message: "Failed to open portal.", type: "error" });
    } finally {
      setPortalLoading(false);
    }
  };

  if (loading) return <Spinner />;

  const currentPlan = sub?.plan ?? "free";
  const yearlySavings = (plan: PlanCard) => {
    const monthlyAnnual = plan.monthlyPrice * 12;
    const saving = monthlyAnnual - plan.yearlyPrice;
    return saving > 0 ? saving : 0;
  };

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Billing &amp; Plans</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Manage your subscription and view plan details.
        </p>
      </div>

      {/* Current plan */}
      {sub && (
        <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-medium text-zinc-500">
                Current Plan
              </p>
              <div className="mt-1 flex items-center gap-3">
                <span className="text-xl font-bold text-white">
                  {sub.plan_name}
                </span>
                <StatusBadge status={sub.status} />
              </div>
              {sub.current_period_end && (
                <p className="mt-2 text-xs text-zinc-500">
                  {sub.cancel_at_period_end
                    ? "Ends on "
                    : "Renews on "}
                  {new Date(sub.current_period_end).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handlePortal}
                disabled={portalLoading}
                className="inline-flex items-center gap-1.5 rounded-xl border border-white/[0.08] px-4 py-2 text-xs font-medium text-zinc-300 transition-all hover:border-white/[0.15] hover:text-white disabled:opacity-50"
              >
                {portalLoading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <ExternalLink className="h-3.5 w-3.5" />
                )}
                Manage Subscription
              </button>
              <button
                onClick={fetchSub}
                className="inline-flex items-center gap-1.5 rounded-xl border border-white/[0.06] p-2 text-zinc-500 transition-all hover:text-white"
                title="Refresh"
              >
                <RefreshCw className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Billing period toggle */}
      <div className="flex items-center justify-center gap-4">
        <span
          className={`text-sm font-medium transition-colors ${
            !isYearly ? "text-white" : "text-zinc-500"
          }`}
        >
          Monthly
        </span>
        <button
          onClick={() => setIsYearly(!isYearly)}
          className={`relative h-7 w-12 rounded-full transition-all ${
            isYearly ? "bg-emerald-500" : "bg-white/[0.1]"
          }`}
        >
          <span
            className={`absolute top-0.5 h-6 w-6 rounded-full bg-white shadow-md transition-all ${
              isYearly ? "left-[22px]" : "left-0.5"
            }`}
          />
        </button>
        <span
          className={`flex items-center gap-2 text-sm font-medium transition-colors ${
            isYearly ? "text-white" : "text-zinc-500"
          }`}
        >
          Yearly
          <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
            Save 30%
          </span>
        </span>
      </div>

      {/* Plan cards */}
      <div className="grid gap-6 lg:grid-cols-3">
        {PLANS.map((plan) => {
          const price = isYearly ? plan.yearlyPrice : plan.monthlyPrice;
          const isCurrent = currentPlan === plan.id;
          const saving = yearlySavings(plan);

          return (
            <div
              key={plan.id}
              className={`relative flex flex-col rounded-2xl border p-6 transition-all ${
                plan.popular
                  ? "border-emerald-500/40 bg-emerald-500/[0.04] shadow-lg shadow-emerald-500/5"
                  : "border-white/[0.06] bg-[#111] hover:border-white/[0.12]"
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="rounded-full bg-emerald-500 px-3.5 py-1 text-xs font-semibold text-black">
                    Most Popular
                  </span>
                </div>
              )}

              {/* Icon */}
              <div
                className={`mb-4 flex h-10 w-10 items-center justify-center rounded-xl ${
                  plan.popular
                    ? "bg-emerald-500/20 text-emerald-400"
                    : "bg-white/[0.04] text-zinc-500"
                }`}
              >
                <plan.icon className="h-5 w-5" />
              </div>

              <h3 className="text-lg font-semibold text-white">{plan.name}</h3>

              {/* Price */}
              <div className="mt-3 flex items-baseline gap-1">
                <span className="text-3xl font-bold text-white">
                  ${price}
                </span>
                {price > 0 && (
                  <span className="text-sm text-zinc-500">
                    /{isYearly ? "year" : "month"}
                  </span>
                )}
              </div>
              {isYearly && saving > 0 && (
                <p className="mt-1 text-xs text-emerald-400">
                  Save ${saving}/year vs monthly
                </p>
              )}

              {/* Features */}
              <ul className="mt-6 flex-1 space-y-3">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2.5 text-sm">
                    <Check className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-500" />
                    <span className="text-zinc-300">{f}</span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <button
                onClick={() =>
                  isCurrent ? null : handleCheckout(plan.id)
                }
                disabled={isCurrent || checkoutLoading !== null}
                className={`mt-8 w-full rounded-xl py-3 text-sm font-semibold transition-all ${
                  isCurrent
                    ? "cursor-default bg-white/[0.04] text-zinc-500"
                    : plan.popular
                      ? "bg-gradient-to-r from-emerald-500 to-emerald-400 text-black shadow-lg shadow-emerald-500/25 hover:from-emerald-400 hover:to-emerald-300"
                      : "border border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-white"
                }`}
              >
                {checkoutLoading === plan.id ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Redirecting...
                  </span>
                ) : isCurrent ? (
                  "Current Plan"
                ) : (
                  plan.cta
                )}
              </button>
            </div>
          );
        })}
      </div>

      {/* Feature comparison grid */}
      <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-6">
        <h2 className="mb-6 text-lg font-semibold text-white">
          Feature Comparison
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/[0.06]">
                <th className="pb-3 pr-6 font-medium text-zinc-500">Feature</th>
                <th className="pb-3 px-4 text-center font-medium text-zinc-500">
                  Free
                </th>
                <th className="pb-3 px-4 text-center font-medium text-emerald-400">
                  Pro
                </th>
                <th className="pb-3 pl-4 text-center font-medium text-zinc-500">
                  Quant
                </th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Backtests per day", "5", "Unlimited", "Unlimited"],
                ["Markets", "US Equities", "Global + Crypto", "Global + Crypto"],
                ["Strategies", "3 built-in", "All + custom params", "All + custom scripts"],
                ["Data sources", "CSV upload", "CSV + Yahoo Finance", "CSV + Yahoo + API"],
                ["Metrics", "Basic", "Advanced (Sortino, VaR)", "Advanced"],
                ["Walk-forward analysis", "—", "✓", "✓"],
                ["PDF export", "—", "✓", "✓"],
                ["API access", "—", "—", "✓"],
                ["Priority support", "—", "✓", "✓"],
                ["SLA guarantee", "—", "—", "✓"],
              ].map(([feature, freeVal, proVal, quantVal]) => (
                <tr
                  key={feature}
                  className="border-b border-white/[0.02] transition-colors hover:bg-white/[0.02]"
                >
                  <td className="py-3 pr-6 font-medium text-zinc-300">
                    {feature}
                  </td>
                  <td className="py-3 px-4 text-center text-zinc-500">
                    {freeVal}
                  </td>
                  <td className="py-3 px-4 text-center text-emerald-400 font-medium">
                    {proVal}
                  </td>
                  <td className="py-3 pl-4 text-center text-zinc-400">
                    {quantVal}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Test card info */}
      <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-6">
        <div className="flex items-start gap-3">
          <Shield className="mt-0.5 h-5 w-5 text-zinc-500" />
          <div>
            <h3 className="text-sm font-semibold text-zinc-300">
              Test Mode — Stripe Test Cards
            </h3>
            <p className="mt-1 text-xs text-zinc-500">
              Use these test card numbers in Stripe test mode. No real charges
              will be made.
            </p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {[
                { label: "Visa (success)", value: "4242 4242 4242 4242" },
                { label: "Visa (declined)", value: "4000 0000 0000 0002" },
                { label: "3D Secure", value: "4000 0000 0000 3220" },
                { label: "Exp / CVC", value: "Any future date / Any 3 digits" },
              ].map((card) => (
                <div
                  key={card.value}
                  className="rounded-lg bg-white/[0.03] px-3 py-2"
                >
                  <p className="text-[10px] text-zinc-600">{card.label}</p>
                  <p className="mt-0.5 font-mono text-xs text-zinc-300">
                    {card.value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}

export default function BillingPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <BillingPageInner />
    </Suspense>
  );
}
