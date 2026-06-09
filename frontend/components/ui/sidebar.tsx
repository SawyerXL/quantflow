"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  BarChart3,
  Settings,
  CreditCard,
  LogOut,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/hooks/use-auth";

function NavItems() {
  const { user } = useAuth();
  const items = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/backtest", label: "Backtest", icon: BarChart3 },
    { href: "/optimize", label: "Optimize", icon: Sparkles, badge: user?.plan === "free" ? "Pro" : null },
    { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
    { href: "/dashboard/settings", label: "Settings", icon: Settings },
  ];
  return (
    <nav className="flex-1 space-y-1 px-3 py-4">
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-zinc-400 hover:bg-white/[0.06] hover:text-white transition-colors"
        >
          <item.icon className="h-4 w-4" />
          {item.label}
          {item.badge && (
            <span className="ml-auto rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-amber-400">{item.badge}</span>
          )}
        </Link>
      ))}
    </nav>
  );
}

export function Sidebar() {
  const { logout } = useAuth();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    await logout();
    router.push("/");
  }

  return (
    <aside className="flex w-64 flex-col border-r border-white/[0.06] bg-[#0a0a0a]">
      {/* Logo */}
      <div className="flex h-14 items-center border-b border-white/[0.06] px-6">
        <Link href="/" className="text-lg font-bold text-emerald-400">
          Quant<span className="text-white">Flow</span>
        </Link>
      </div>

      {/* Nav */}
      <NavItems />

      {/* Sign Out */}
      <div className="border-t border-white/[0.06] px-3 py-4">
        <button
          onClick={handleSignOut}
          disabled={signingOut}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-zinc-500 hover:bg-red-500/10 hover:text-red-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {signingOut ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Signing out...
            </>
          ) : (
            <>
              <LogOut className="h-4 w-4" />
              Sign Out
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
