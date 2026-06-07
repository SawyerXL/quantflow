"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { X, TrendingUp, BarChart3, Zap } from "lucide-react";

interface AuthModalProps {
  open: boolean;
  onClose: () => void;
}

export function AuthModal({ open, onClose }: AuthModalProps) {
  const router = useRouter();

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  // Prevent body scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[100] flex items-end justify-center sm:items-center">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
          />

          {/* Card */}
          <motion.div
            initial={{ opacity: 0, y: 60, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 40, scale: 0.95 }}
            transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="relative z-10 w-full max-w-md rounded-t-2xl sm:rounded-2xl border border-white/[0.08] bg-[#111] p-6 shadow-2xl sm:mx-4"
          >
            {/* Close button */}
            <button
              onClick={onClose}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-zinc-500 transition-colors hover:bg-white/[0.08] hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>

            {/* Content */}
            <div className="text-center">
              {/* Icon */}
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10">
                <TrendingUp className="h-7 w-7 text-emerald-400" />
              </div>

              <h2 className="text-xl font-bold text-white">
                Sign in to run backtests
              </h2>
              <p className="mt-2 text-sm text-zinc-400">
                Create a free account to get{" "}
                <span className="font-semibold text-emerald-400">5 backtests per day</span>
              </p>

              {/* Feature pills */}
              <div className="mt-5 flex flex-wrap justify-center gap-2">
                {[
                  { icon: BarChart3, label: "3 Strategies" },
                  { icon: Zap, label: "Instant Results" },
                  { icon: TrendingUp, label: "Free Forever" },
                ].map((f) => (
                  <span
                    key={f.label}
                    className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-xs text-zinc-300"
                  >
                    <f.icon className="h-3 w-3 text-emerald-400" />
                    {f.label}
                  </span>
                ))}
              </div>

              {/* Buttons */}
              <div className="mt-6 space-y-3">
                <button
                  onClick={() => router.push("/register")}
                  className="w-full rounded-xl bg-gradient-to-r from-emerald-500 to-emerald-400 py-3 text-sm font-semibold text-black shadow-lg shadow-emerald-500/25 transition-all hover:from-emerald-400 hover:to-emerald-300"
                >
                  Create Free Account
                </button>
                <button
                  onClick={() => router.push("/login")}
                  className="w-full rounded-xl border border-zinc-700 bg-transparent py-3 text-sm font-medium text-zinc-300 transition-all hover:border-zinc-500 hover:text-white"
                >
                  Sign In
                </button>
              </div>

              <p className="mt-4 text-xs text-zinc-600">
                No credit card required
              </p>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
