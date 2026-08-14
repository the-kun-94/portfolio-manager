import type {
  SignalOut,
  HoldingOut,
  TransactionOut,
  CashSummary,
  TradeCreate,
  SectorRankOut,
  ReinvestmentRecommendationOut,
  ParkCashRequest,
  UnparkRequest,
  PerformanceHistoryOut,
} from "./types";
import { traceStart, traceSettle } from "./loadTrace";

// Every request goes through our own same-origin proxy (/api/proxy/*)
// instead of hitting the backend directly — the proxy attaches the
// correct backend API key server-side based on the visitor's session
// role, so the key itself never ships in the browser bundle. See
// pages/api/proxy/[...path].ts.
const API_BASE_URL = "/api/proxy";

// The Render free-tier backend spins down after ~15 min idle and can take
// 30-60s to cold-start on the next request. The proxy above runs on
// Vercel's Edge runtime, whose own execution cap (~25s) is shorter than
// that cold-start window, so a single fetch attempt on a cold backend gets
// killed by Vercel before Render finishes booting. We keep each attempt
// under that cap and retry (with backoff) until either it succeeds or a
// generous overall budget runs out, so a cold start shows up as automatic
// retries instead of a hard error.
const ATTEMPT_TIMEOUT_MS = 20_000;
const MAX_WAIT_MS = 90_000;
const RETRY_DELAYS_MS = [1_000, 2_000, 4_000, 8_000];

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

function isRetryableStatus(status: number): boolean {
  // 502/503/504 are what a not-yet-ready backend (or the platform in front
  // of it) tends to answer with while it's still booting.
  return status === 502 || status === 503 || status === 504;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

interface AttemptResult<T> {
  ok: boolean;
  data?: T;
  error?: ApiError;
  retryable: boolean;
}

async function attemptOnce<T>(path: string, options: RequestInit | undefined): Promise<AttemptResult<T>> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ATTEMPT_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
      signal: controller.signal,
    });

    if (!res.ok) {
      let detail = "";
      try {
        const body = await res.json();
        detail = body?.detail || JSON.stringify(body);
      } catch {
        detail = await res.text().catch(() => "");
      }
      return {
        ok: false,
        error: new ApiError(res.status, detail || `Request to ${path} failed (${res.status})`),
        retryable: isRetryableStatus(res.status),
      };
    }

    return { ok: true, data: (await res.json()) as T, retryable: false };
  } catch (err) {
    const timedOut = err instanceof DOMException && err.name === "AbortError";
    return {
      ok: false,
      error: new ApiError(
        0,
        timedOut ? "Timed out waiting for the Engine to respond." : "Could not reach the app. Check your connection."
      ),
      retryable: true,
    };
  } finally {
    clearTimeout(timer);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const method = options?.method ?? "GET";
  const deadline = Date.now() + MAX_WAIT_MS;
  let attempt = 0;

  while (true) {
    attempt += 1;
    traceStart(method, path, attempt);
    const result = await attemptOnce<T>(path, options);

    if (result.ok) {
      traceSettle(method, path, "ok", null);
      return result.data as T;
    }

    const error = result.error as ApiError;
    const timeLeft = deadline - Date.now();
    if (!result.retryable || timeLeft <= 0) {
      traceSettle(method, path, "error", error.message);
      throw error;
    }

    traceSettle(method, path, "error", `${error.message} — retrying (likely a cold start)`);
    const delay = RETRY_DELAYS_MS[Math.min(attempt - 1, RETRY_DELAYS_MS.length - 1)];
    await sleep(Math.min(delay, Math.max(timeLeft, 0)));
  }
}

export const api = {
  decisionEngine: (onlyActionable = false) =>
    request<SignalOut[]>(`/api/decision-engine?only_actionable=${onlyActionable}`),

  holdings: () => request<HoldingOut[]>("/api/holdings"),

  cashSummary: () => request<CashSummary>("/api/cash-summary"),

  recentTrades: (limit = 10) =>
    request<TransactionOut[]>(`/api/trades/recent?limit=${limit}`),

  sectorStrength: () => request<SectorRankOut[]>("/api/sector-strength"),

  createTrade: (trade: TradeCreate) =>
    request<TransactionOut>("/api/trades", {
      method: "POST",
      body: JSON.stringify(trade),
    }),

  reinvestmentRecommendation: () =>
    request<ReinvestmentRecommendationOut>("/api/reinvestment/recommendation"),

  parkCash: (body: ParkCashRequest) =>
    request<TransactionOut>("/api/reinvestment/park", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  unparkCash: (body: UnparkRequest) =>
    request<TransactionOut>("/api/reinvestment/unpark", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  performanceHistory: () => request<PerformanceHistoryOut>("/api/performance/history"),
};

export { ApiError };
