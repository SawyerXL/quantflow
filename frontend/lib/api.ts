// On Vercel: use relative paths, proxied through vercel.json rewrites
// On local dev: use absolute localhost URL
function resolveApiUrl(): string {
  if (typeof window !== "undefined" && window.location.hostname === "localhost") {
    return "http://localhost:8000/api/v1";
  }
  // Production (Vercel proxy) or SSR: use relative path
  return "/api/v1";
}
export const API_URL = resolveApiUrl();

// Render free tier spins down after 15 min of inactivity.
// Cold start can take 30+ seconds — we retry up to 3 times with a long timeout.
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 2000;
const REQUEST_TIMEOUT_MS = 60_000; // 60 seconds for Render cold start

interface RequestOptions extends RequestInit {
  token?: string;
}

export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = "APIError";
  }
}

async function request<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const { token, ...fetchOptions } = options;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...fetchOptions.headers,
  };

  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  let lastError: Error | null = null;

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    try {
      const res = await fetch(`${API_URL}${endpoint}`, {
        ...fetchOptions,
        headers,
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const error = body.error ?? body.detail ?? { message: res.statusText };
        throw new APIError(res.status, error.message || "Request failed", error);
      }

      const body = await res.json();
      // Unwrap unified response format
      if (body.success !== undefined) {
        return body.data as T;
      }
      return body as T;
    } catch (error) {
      lastError = error as Error;

      // Don't retry client errors (4xx)
      if (error instanceof APIError && error.status >= 400 && error.status < 500) {
        throw error;
      }

      // Don't retry if it's the last attempt
      if (attempt < MAX_RETRIES - 1) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
      }
    }
  }

  throw lastError ?? new Error("Request failed after retries");
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    request<{ access_token: string; refresh_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string, full_name?: string) =>
    request<{ id: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  refreshToken: (refresh_token: string) =>
    request<{ access_token: string }>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }),

  getMe: (token: string) =>
    request<{ id: string; email: string; plan: string }>("/auth/me", { token }),

  // Backtest
  runBacktest: (formData: FormData) =>
    request<{ id: string }>("/backtest/run", {
      method: "POST",
      body: formData,
      headers: {}, // Let browser set multipart Content-Type
    }),

  getBacktest: (id: string) => request(`/backtest/${id}`),

  listBacktests: (page = 1, limit = 20) =>
    request<{ items: unknown[]; total: number }>(
      `/backtest/list?page=${page}&limit=${limit}`,
    ),

  // Data
  searchSymbols: (query: string) =>
    request<{ results: Array<{ symbol: string; name: string }> }>(
      `/data/search?q=${encodeURIComponent(query)}`,
    ),

  // Billing
  getSubscription: () => request("/billing/subscription"),

  createCheckout: (plan: string, billingPeriod: string) =>
    request<{ checkout_url: string }>("/billing/checkout", {
      method: "POST",
      body: JSON.stringify({ plan, billing_period: billingPeriod }),
    }),

  createPortal: () =>
    request<{ portal_url: string }>("/billing/portal", {
      method: "POST",
    }),
};

/**
 * Check if the backend is awake. Render cold-start can take 30s.
 * Call this on app load to warm up the backend.
 */
export async function warmupBackend(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL.replace("/api/v1", "")}/health`, {
      signal: AbortSignal.timeout(10_000),
    });
    return res.ok;
  } catch {
    return false;
  }
}
