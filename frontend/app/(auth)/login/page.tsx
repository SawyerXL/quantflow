"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    const form = new FormData(e.currentTarget);
    const email = form.get("email") as string;
    const password = form.get("password") as string;

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/auth/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        },
      );
      if (res.ok) {
        router.push("/dashboard");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center">
          <Link href="/" className="text-2xl font-bold text-brand-600">
            QuantFlow
          </Link>
          <h1 className="mt-6 text-2xl font-bold text-surface-900">
            Welcome back
          </h1>
          <p className="mt-2 text-sm text-surface-500">
            Sign in to your account
          </p>
        </div>
        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-surface-700"
            >
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              className="input-field mt-1"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-surface-700"
            >
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              className="input-field mt-1"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-surface-500">
          Don&apos;t have an account?{" "}
          <Link
            href="/register"
            className="font-medium text-brand-600 hover:text-brand-500"
          >
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
