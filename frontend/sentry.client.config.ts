import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Free tier: 5,000 errors/month — sample conservatively
  tracesSampleRate: 0.1,
  replaysSessionSampleRate: 0.05,
  replaysOnErrorSampleRate: 1.0,

  environment: process.env.NODE_ENV || "development",

  // Filter noise from the free-tier quota
  ignoreErrors: [
    "ResizeObserver loop limit exceeded",
    "ResizeObserver loop completed with undelivered notifications",
    "Network request failed",
    "Failed to fetch",
    "AbortError",
    "Loading chunk",
    "Non-Error promise rejection captured",
  ],

  // Don't send PII
  beforeSend(event) {
    // Strip URLs that might contain tokens
    if (event.request?.url) {
      event.request.url = event.request.url.replace(/token=[^&]*/, "token=[redacted]");
    }
    return event;
  },
});
