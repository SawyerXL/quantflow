"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { API_URL } from "@/lib/api";

type FieldErrors = {
  email?: string;
  password?: string;
};

function validateEmail(v: string): string | null {
  if (!v) return "Email is required";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return "Please enter a valid email (e.g., you@example.com)";
  return null;
}

function validatePassword(v: string): string | null {
  if (!v) return "Password is required";
  if (v.length < 8) return "Password must be at least 8 characters";
  if (!/[A-Za-z]/.test(v)) return "Password must contain at least one letter";
  if (!/\d/.test(v)) return "Password must contain at least one digit";
  return null;
}

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [serverError, setServerError] = useState("");

  function handleFieldChange(field: "email" | "password", value: string) {
    const err =
      field === "email" ? validateEmail(value) : validatePassword(value);
    setErrors((prev) => ({ ...prev, [field]: err }));
    setServerError("");
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setServerError("");

    const form = new FormData(e.currentTarget);
    const email = (form.get("email") as string).trim();
    const password = form.get("password") as string;
    const name = (form.get("name") as string).trim();

    // Validate all fields before submit
    const emailErr = validateEmail(email);
    const passwordErr = validatePassword(password);
    setErrors({ email: emailErr, password: passwordErr });
    if (emailErr || passwordErr) return;

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, full_name: name || null }),
      });

      const data = await res.json();

      if (res.ok) {
        router.push("/login?registered=1");
      } else {
        const detail = data?.error ?? data?.detail ?? {};
        const msg = detail?.message ?? detail ?? "Registration failed";
        if (res.status === 409 || msg.toLowerCase().includes("already")) {
          setErrors((prev) => ({ ...prev, email: "An account with this email already exists" }));
        } else {
          setServerError(typeof msg === "string" ? msg : JSON.stringify(msg));
        }
      }
    } catch {
      setServerError("Network error. Please check your connection and try again.");
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
          <h1 className="mt-6 text-2xl font-bold text-white">
            Create your account
          </h1>
          <p className="mt-2 text-sm text-zinc-400">
            Start your free trial today
          </p>
        </div>

        {/* Server error banner */}
        {serverError && (
          <div className="mt-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {serverError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-5" noValidate>
          {/* Name */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-zinc-400">
              Name
            </label>
            <input
              id="name"
              name="name"
              type="text"
              className="mt-1.5 w-full rounded-xl border border-white/[0.08] bg-[#0f0f0f] px-4 py-2.5 text-sm text-white placeholder-zinc-600 outline-none transition-all focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/30"
              placeholder="John Doe"
            />
          </div>

          {/* Email */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-zinc-400">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="text"
              autoComplete="email"
              className={`mt-1.5 w-full rounded-xl border bg-[#0f0f0f] px-4 py-2.5 text-sm text-white placeholder-zinc-600 outline-none transition-all focus:ring-1 ${
                errors.email
                  ? "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/30"
                  : "border-white/[0.08] focus:border-emerald-500/50 focus:ring-emerald-500/30"
              }`}
              placeholder="you@example.com"
              onChange={(e) => handleFieldChange("email", e.target.value)}
            />
            {errors.email && (
              <p className="mt-1.5 text-xs text-red-400">{errors.email}</p>
            )}
          </div>

          {/* Password */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-zinc-400">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              className={`mt-1.5 w-full rounded-xl border bg-[#0f0f0f] px-4 py-2.5 text-sm text-white placeholder-zinc-600 outline-none transition-all focus:ring-1 ${
                errors.password
                  ? "border-red-500/50 focus:border-red-500/50 focus:ring-red-500/30"
                  : "border-white/[0.08] focus:border-emerald-500/50 focus:ring-emerald-500/30"
              }`}
              placeholder="••••••••"
              onChange={(e) => handleFieldChange("password", e.target.value)}
            />
            {errors.password ? (
              <p className="mt-1.5 text-xs text-red-400">{errors.password}</p>
            ) : (
              <p className="mt-1.5 text-xs text-zinc-600">
                At least 8 characters, with letters and digits
              </p>
            )}
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="mt-2 w-full rounded-xl bg-emerald-500 py-3 text-sm font-semibold text-black transition-all hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-zinc-500">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-emerald-400 hover:text-emerald-300">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
