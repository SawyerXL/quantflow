import Link from "next/link";
import {
  LayoutDashboard,
  BarChart3,
  Settings,
  CreditCard,
  LogOut,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/backtest", label: "Backtest", icon: BarChart3 },
  { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r border-surface-200 bg-white">
        <div className="flex h-14 items-center border-b border-surface-200 px-6">
          <Link href="/" className="text-lg font-bold text-brand-600">
            QuantFlow
          </Link>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-surface-600 hover:bg-surface-100 hover:text-surface-900 transition-colors"
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="border-t border-surface-200 px-3 py-4">
          <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-surface-500 hover:bg-surface-100 hover:text-red-600 transition-colors">
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto bg-surface-50 p-8">
        {children}
      </main>
    </div>
  );
}
