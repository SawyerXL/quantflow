"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { API_URL } from "@/lib/api";
import {
  Loader2,
  CheckCircle,
  Eye,
  EyeOff,
  ShieldAlert,
  ArrowLeft,
} from "lucide-react";

function ResetPasswordInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [pwd, setPwd] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [countdown, setCountdown] = useState(3);

  // Validate token on mount
  useEffect(() => {
    if (!token) {
      setError("No reset token found. Please use the link from your email.");
      setLoading(false);
      return;
    }
    if (token.length < 32) {
      setError("Invalid reset link. Please request a new one.");
      setLoading(false);
      return;
    }
    setLoading(false);
  }, [token]);

  // Auto-redirect after success
  useEffect(() => {
    if (!success) return;
    if (countdown <= 0) { router.push("/login"); return; }
    const iv = setInterval(() => setCountdown((c) => c - 1), 1000);
    return () => clearInterval(iv);
  }, [success, countdown, router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    // Client-side validation
    if (pwd.length < 8) { setError("Password must be at least 8 characters"); return; }
    if (!/[A-Za-z]/.test(pwd)) { setError("Password must contain at least one letter"); return; }
    if (!/\d/.test(pwd)) { setError("Password must contain at least one digit"); return; }
    if (pwd !== confirm) { setError("Passwords do not match"); return; }

    setSubmitting(true);
    try {
      const res = await fetch(`${API_URL}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: pwd }),
      });

      const data = await res.json();
      if (res.ok && data.success) {
        setSuccess(true);
      } else {
        const detail = data?.error ?? data?.detail ?? {};
        const msg = detail?.message ?? detail ?? "Reset failed";
        setError(typeof msg === "string" ? msg : "Reset failed. Please request a new link.");
      }
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function strength(p: string) {
    let s = 0;
    if (p.length >= 8) s++;
    if (p.length >= 12) s++;
    if (/[A-Z]/.test(p)) s++;
    if (/[a-z]/.test(p)) s++;
    if (/\d/.test(p)) s++;
    if (/[^A-Za-z0-9]/.test(p)) s++;
    if (s <= 2) return { label: "Weak", color: "bg-red-500", width: "w-1/4" };
    if (s <= 4) return { label: "Medium", color: "bg-amber-500", width: "w-2/4" };
    return { label: "Strong", color: "bg-emerald-500", width: "w-full" };
  }

  const pwdStrength = strength(pwd);

  // ── Success state ──
  if (success) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4 bg-[#0a0a0a]">
        <div className="w-full max-w-sm text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10">
            <CheckCircle className="h-8 w-8 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Password reset successful!</h1>
          <p className="mt-2 text-sm text-zinc-400">
            You can now sign in with your new password.
          </p>
          <p className="mt-4 text-sm text-zinc-500">
            Redirecting in {countdown}s...
          </p>
          <Link href="/login" className="mt-4 inline-block text-sm font-medium text-emerald-400 hover:text-emerald-300">
            Go to Sign In now
          </Link>
        </div>
      </div>
    );
  }

  // ── Invalid token ──
  if (!loading && !token) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4 bg-[#0a0a0a]">
        <div className="w-full max-w-sm text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-red-500/10">
            <ShieldAlert className="h-8 w-8 text-red-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Invalid reset link</h1>
          <p className="mt-2 text-sm text-zinc-400">
            {error || "The reset link is missing or invalid. Please request a new one."}
          </p>
          <Link href="/forgot-password" className="mt-6 inline-block rounded-xl bg-emerald-500 px-6 py-3 text-sm font-semibold text-black hover:bg-emerald-400">
            Request New Link
          </Link>
        </div>
      </div>
    );
  }

  // ── Loading ──
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#0a0a0a]">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  // ── Form state ──
  return (
    <div className="flex min-h-screen items-center justify-center px-4 bg-[#0a0a0a]">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-white">Reset your password</h1>
        <p className="mt-2 text-sm text-zinc-400">Enter your new password below.</p>

        {error && (
          <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error === "Invalid or expired reset link. Please request a new one."
              ? (<>{error} <Link href="/forgot-password" className="underline hover:text-red-300">Request new link</Link></>)
              : error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          {/* New password */}
          <div>
            <label className="block text-sm font-medium text-zinc-400">New Password</label>
            <div className="relative mt-1.5">
              <input
                type={showPwd ? "text" : "password"}
                value={pwd}
                onChange={(e) => setPwd(e.target.value)}
                className="w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] py-2.5 pl-4 pr-10 text-sm text-white placeholder-zinc-600 outline-none transition-all focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30"
                placeholder="••••••••"
              />
              <button type="button" onClick={() => setShowPwd(!showPwd)} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300">
                {showPwd ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {/* Strength bar */}
            {pwd && (
              <div className="mt-2">
                <div className="h-1.5 w-full rounded-full bg-white/[0.06]">
                  <div className={`h-1.5 rounded-full transition-all ${pwdStrength.color} ${pwdStrength.width}`} />
                </div>
                <p className="mt-1 text-xs text-zinc-500">Strength: <span className={pwdStrength.label === "Strong" ? "text-emerald-400" : pwdStrength.label === "Medium" ? "text-amber-400" : "text-red-400"}>{pwdStrength.label}</span></p>
              </div>
            )}
          </div>

          {/* Confirm password */}
          <div>
            <label className="block text-sm font-medium text-zinc-400">Confirm Password</label>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className={`mt-1.5 w-full rounded-xl border bg-[#0f0f0f] py-2.5 pl-4 pr-4 text-sm text-white placeholder-zinc-600 outline-none transition-all focus:ring-1 ${
                confirm && pwd !== confirm
                  ? "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/30"
                  : "border-white/[0.08] focus:border-emerald-500/50 focus:ring-emerald-500/30"
              }`}
              placeholder="••••••••"
            />
            {confirm && pwd !== confirm && (
              <p className="mt-1 text-xs text-red-400">Passwords do not match</p>
            )}
          </div>

          <button type="submit" disabled={submitting} className="w-full rounded-xl bg-emerald-500 py-3 text-sm font-semibold text-black transition-all hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed">
            {submitting ? <span className="inline-flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" />Resetting...</span> : "Reset Password"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-zinc-500">
          <Link href="/login" className="inline-flex items-center gap-1 text-zinc-500 hover:text-zinc-300">
            <ArrowLeft className="h-3 w-3" /> Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center bg-[#0a0a0a]">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
      </div>
    }>
      <ResetPasswordInner />
    </Suspense>
  );
}
