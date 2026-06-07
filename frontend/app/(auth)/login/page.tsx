"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { API_URL } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";

export default function LoginPage() {
  const router = useRouter();
  const auth = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const form = new FormData(e.currentTarget);
    const email = (form.get("email") as string).trim();
    const password = form.get("password") as string;

    // Basic frontend validation
    if (!email) { setError("Please enter your email"); setLoading(false); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setError("Please enter a valid email address"); setLoading(false); return; }
    if (!password) { setError("Please enter your password"); setLoading(false); return; }

    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        await auth.login(data.data.access_token, data.data.refresh_token);
        router.push("/dashboard");
      } else {
        const detail = data?.error ?? data?.detail ?? {};
        const msg = detail?.message ?? detail ?? "Invalid email or password";
        setError(typeof msg === "string" ? msg : "Invalid email or password");
      }
    } catch {
      setError("Network error. Please check your connection.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4 bg-[#0a0a0a]">
      <div className="w-full max-w-sm">
        <div className="text-center">
          <Link href="/" className="text-2xl font-bold text-emerald-400">
            Quant<span className="text-white">Flow</span>
          </Link>
          <h1 className="mt-6 text-2xl font-bold text-white">Welcome back</h1>
          <p className="mt-2 text-sm text-zinc-400">Sign in to your account</p>
        </div>

        {/* Error banner */}
        {error && (
          <div className="mt-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-5" noValidate>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-zinc-400">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="text"
              autoComplete="email"
              className="mt-1.5 w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] px-4 py-2.5 text-sm text-white placeholder-zinc-600 outline-none transition-all focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-zinc-400">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              className="mt-1.5 w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] px-4 py-2.5 text-sm text-white placeholder-zinc-600 outline-none transition-all focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30"
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="mt-2 w-full rounded-xl bg-emerald-500 py-3 text-sm font-semibold text-black transition-all hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-zinc-500">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="font-medium text-emerald-400 hover:text-emerald-300">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
