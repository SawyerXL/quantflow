"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

// ============================================================================
// Types
// ============================================================================

interface AuthUser {
  id: string;
  email: string;
  full_name: string | null;
  plan: "free" | "pro" | "quant";
  backtest_count_today: number;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  isLoggedIn: boolean;
  login: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  isLoggedIn: false,
  login: async () => {},
  logout: () => {},
  refreshUser: async () => {},
});

// ============================================================================
// Provider
// ============================================================================

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const API_URL =
        process.env.NEXT_PUBLIC_API_URL ||
        (typeof window !== "undefined" && window.location.hostname === "localhost"
          ? "http://localhost:8000/api/v1"
          : "/api/v1");

      // Short timeout — don't block page load on cold Render startup
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const res = await fetch(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const json = await res.json();
        const data = json.data ?? json;
        setUser({
          id: data.id,
          email: data.email,
          full_name: data.full_name ?? null,
          plan: data.plan ?? "free",
          backtest_count_today: data.backtest_count_today ?? 0,
        });
      } else {
        // Token expired or invalid — clear
        localStorage.removeItem("token");
        localStorage.removeItem("refresh");
        setUser(null);
      }
    } catch (err: any) {
      // Timeout or network error — keep token but defer API call
      // User can still browse static pages; auth checked on Run Backtest
      if (err?.name !== "AbortError") {
        console.debug("Auth check failed, deferring");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = useCallback(
    async (accessToken: string, refreshToken: string) => {
      localStorage.setItem("token", accessToken);
      localStorage.setItem("refresh", refreshToken);
      await fetchUser();
    },
    [fetchUser],
  );

  const logout = useCallback(async () => {
    const token = localStorage.getItem("token");
    // Best-effort server-side logout (token blacklisting for future)
    if (token) {
      try {
        const API_URL =
          typeof window !== "undefined" && window.location.hostname === "localhost"
            ? "http://localhost:8000/api/v1"
            : "/api/v1";
        await fetch(`${API_URL}/auth/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        // Even if the server call fails, clear local state
      }
    }
    localStorage.removeItem("token");
    localStorage.removeItem("refresh");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isLoggedIn: user !== null,
        login,
        logout,
        refreshUser: fetchUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ============================================================================
// Hook
// ============================================================================

export function useAuth() {
  return useContext(AuthContext);
}
