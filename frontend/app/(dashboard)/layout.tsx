"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard, BarChart3, Settings, CreditCard, LogOut, Loader2,
  Sparkles, Menu, X,
} from "lucide-react";
import { useAuth } from "@/hooks/use-auth";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/backtest", label: "Backtest", icon: BarChart3 },
  { href: "/optimize", label: "Optimize", icon: Sparkles },
  { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() { setSigningOut(true); await logout(); router.push("/"); }

  return (
    <div className="flex min-h-screen bg-[#0c0c0c]">
      {/* Sidebar overlay — mobile */}
      {menuOpen && (
        <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setMenuOpen(false)} />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-white/[0.06] bg-[#0a0a0a] transition-transform duration-200 lg:relative lg:translate-x-0 ${
          menuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-14 items-center justify-between border-b border-white/[0.06] px-6">
          <Link href="/" className="text-lg font-bold text-emerald-400" onClick={() => setMenuOpen(false)}>
            Quant<span className="text-white">Flow</span>
          </Link>
          <button onClick={() => setMenuOpen(false)} className="rounded-lg p-1.5 text-zinc-500 hover:text-white lg:hidden">
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-zinc-400 hover:bg-white/[0.06] hover:text-white transition-colors"
            >
              <item.icon className="h-4 w-4" />
              {item.label}
              {item.label === "Optimize" && user?.plan === "free" && (
                <span className="ml-auto rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-amber-400">Pro</span>
              )}
            </Link>
          ))}
        </nav>

        <div className="border-t border-white/[0.06] px-3 py-4">
          <button
            onClick={handleSignOut}
            disabled={signingOut}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-zinc-500 hover:bg-red-500/10 hover:text-red-400 disabled:opacity-50 transition-colors"
          >
            {signingOut ? <><Loader2 className="h-4 w-4 animate-spin" />Signing out...</> : <><LogOut className="h-4 w-4" />Sign Out</>}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto px-4 py-6 lg:px-8 lg:py-8">
        {/* Mobile top bar */}
        <div className="mb-4 flex items-center gap-3 lg:hidden">
          <button onClick={() => setMenuOpen(true)} className="rounded-lg p-2 text-zinc-400 hover:text-white">
            <Menu className="h-5 w-5" />
          </button>
          <Link href="/" className="text-base font-bold text-emerald-400">
            Quant<span className="text-white">Flow</span>
          </Link>
        </div>
        {children}
      </main>
    </div>
  );
}
