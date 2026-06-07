"use client";

import { useState } from "react";
import Link from "next/link";
import { API_URL } from "@/lib/api";
import { Mail, Loader2, CheckCircle, ArrowLeft } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [cooldown, setCooldown] = useState(0);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Please enter a valid email address");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
      if (res.ok) setSent(true);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function resend() {
    if (cooldown > 0) return;
    await handleSubmit({ preventDefault: () => {} } as React.FormEvent);
    setCooldown(60);
    const iv = setInterval(() => setCooldown((c) => { if (c <= 1) { clearInterval(iv); return 0; } return c - 1; }), 1000);
  }

  // ── Success state ──
  if (sent) {
    return (
      <div className="flex min-h-screen items-center justify-center px-4 bg-[#0a0a0a]">
        <div className="w-full max-w-sm text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10">
            <CheckCircle className="h-8 w-8 text-emerald-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">Check your email</h1>
          <p className="mt-2 text-sm text-zinc-400">
            If an account exists for{" "}
            <span className="font-medium text-white">{email}</span>, we sent a
            reset link.
          </p>
          <p className="mt-4 text-xs text-zinc-500">
            Didn&apos;t receive it? Check spam or{" "}
            <button onClick={resend} disabled={cooldown > 0} className="text-emerald-400 hover:text-emerald-300 disabled:text-zinc-600">
              {cooldown > 0 ? `Resend in ${cooldown}s` : "resend"}
            </button>
          </p>
          <Link href="/login" className="mt-6 inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-300">
            <ArrowLeft className="h-3 w-3" /> Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  // ── Form state ──
  return (
    <div className="flex min-h-screen items-center justify-center px-4 bg-[#0a0a0a]">
      <div className="w-full max-w-sm">
        <Link href="/login" className="mb-6 inline-flex items-center gap-1 text-sm text-zinc-500 hover:text-zinc-300">
          <ArrowLeft className="h-3 w-3" /> Back to sign in
        </Link>

        <h1 className="text-2xl font-bold text-white">Forgot your password?</h1>
        <p className="mt-2 text-sm text-zinc-400">
          Enter your email and we&apos;ll send you a reset link.
        </p>

        {error && (
          <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-zinc-400">Email</label>
            <div className="relative mt-1.5">
              <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] py-2.5 pl-10 pr-4 text-sm text-white placeholder-zinc-600 outline-none transition-all focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30"
                placeholder="you@example.com"
              />
            </div>
          </div>
          <button type="submit" disabled={loading} className="w-full rounded-xl bg-emerald-500 py-3 text-sm font-semibold text-black transition-all hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed">
            {loading ? <span className="inline-flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" />Sending...</span> : "Send Reset Link"}
          </button>
        </form>
      </div>
    </div>
  );
}
