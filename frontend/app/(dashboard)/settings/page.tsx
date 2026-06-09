"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { API_URL } from "@/lib/api";
import {
  User, Mail, Shield, Key, Loader2, Check, AlertCircle,
  Eye, EyeOff, ArrowLeft,
} from "lucide-react";
import Link from "next/link";

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const router = useRouter();

  // Password change state
  const [currentPwd, setCurrentPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [pwdLoading, setPwdLoading] = useState(false);
  const [pwdError, setPwdError] = useState("");
  const [pwdSuccess, setPwdSuccess] = useState("");

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault();
    setPwdError("");
    setPwdSuccess("");

    if (newPwd.length < 8) { setPwdError("Password must be at least 8 characters"); return; }
    if (!/[A-Za-z]/.test(newPwd)) { setPwdError("Password must contain at least one letter"); return; }
    if (!/\d/.test(newPwd)) { setPwdError("Password must contain at least one digit"); return; }
    if (newPwd !== confirmPwd) { setPwdError("Passwords do not match"); return; }

    setPwdLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_URL}/auth/change-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ current_password: currentPwd, new_password: newPwd }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setPwdSuccess("Password changed successfully");
        setCurrentPwd(""); setNewPwd(""); setConfirmPwd("");
      } else {
        setPwdError(data?.error?.message || data?.detail?.message || "Failed to change password");
      }
    } catch {
      setPwdError("Network error");
    } finally {
      setPwdLoading(false);
    }
  }

  return (
    <div className="space-y-8 pb-16">
      <Link href="/dashboard" className="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300">
        <ArrowLeft className="h-3 w-3" /> Dashboard
      </Link>
      <h1 className="text-2xl font-bold text-white">Settings</h1>

      {/* Profile card */}
      <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-6">
        <h2 className="mb-4 text-sm font-semibold text-zinc-300 flex items-center gap-2">
          <User className="h-4 w-4" /> Profile
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <InfoRow label="Email" value={user?.email || "—"} icon={Mail} />
          <InfoRow label="Full Name" value={user?.full_name || "—"} icon={User} />
          <InfoRow label="Plan" value={(user?.plan || "free").toUpperCase()} icon={Shield} />
          <InfoRow label="Backtests Today" value={`${user?.backtest_count_today ?? 0}`} icon={Key} />
        </div>
      </div>

      {/* Change password */}
      <div className="rounded-2xl border border-white/[0.06] bg-[#111] p-6">
        <h2 className="mb-4 text-sm font-semibold text-zinc-300 flex items-center gap-2">
          <Key className="h-4 w-4" /> Change Password
        </h2>

        {pwdError && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-400">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />{pwdError}
          </div>
        )}
        {pwdSuccess && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-400">
            <Check className="h-4 w-4 flex-shrink-0" />{pwdSuccess}
          </div>
        )}

        <form onSubmit={handlePasswordChange} className="space-y-4 max-w-md">
          <InputField label="Current Password" value={currentPwd} onChange={setCurrentPwd} show={showPwd} />
          <InputField label="New Password" value={newPwd} onChange={setNewPwd} show={showPwd} />
          <InputField label="Confirm New Password" value={confirmPwd} onChange={setConfirmPwd} show={showPwd} />

          <label className="flex items-center gap-2 text-xs text-zinc-500 cursor-pointer">
            <input type="checkbox" checked={showPwd} onChange={() => setShowPwd(!showPwd)} className="rounded" />
            Show passwords
          </label>

          <button type="submit" disabled={pwdLoading} className="rounded-xl bg-emerald-500 px-6 py-2.5 text-sm font-semibold text-black hover:bg-emerald-400 disabled:opacity-50">
            {pwdLoading ? <span className="flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" />Changing...</span> : "Change Password"}
          </button>
        </form>
      </div>

      {/* Danger zone */}
      <div className="rounded-2xl border border-red-500/10 bg-[#111] p-6">
        <h2 className="mb-2 text-sm font-semibold text-red-400">Sign Out</h2>
        <p className="text-xs text-zinc-500 mb-4">Sign out of your account on this device.</p>
        <button onClick={async () => { await logout(); router.push("/"); }}
          className="rounded-xl border border-red-500/30 px-6 py-2.5 text-sm font-medium text-red-400 hover:bg-red-500/10 transition-colors">
          Sign Out
        </button>
      </div>
    </div>
  );
}

function InfoRow({ label, value, icon: Icon }: { label: string; value: string; icon: any }) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-white/[0.03] px-4 py-3">
      <Icon className="h-4 w-4 text-zinc-500 flex-shrink-0" />
      <div>
        <p className="text-[11px] text-zinc-500">{label}</p>
        <p className="text-sm font-medium text-white">{value}</p>
      </div>
    </div>
  );
}

function InputField({ label, value, onChange, show }: { label: string; value: string; onChange: (v: string) => void; show: boolean }) {
  return (
    <div>
      <label className="block mb-1 text-xs font-medium text-zinc-400">{label}</label>
      <div className="relative">
        <input type={show ? "text" : "password"} value={value} onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] py-2.5 px-4 pr-10 text-sm text-white outline-none focus:border-emerald-500/50" />
      </div>
    </div>
  );
}
