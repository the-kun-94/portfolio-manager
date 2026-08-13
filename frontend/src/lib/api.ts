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

// Every request goes through our own same-origin proxy (/api/proxy/*)
// instead of hitting the backend directly — the proxy attaches the
// correct backend API key server-side based on the visitor's session
// role, so the key itself never ships in the browser bundle. See
// pages/api/proxy/[...path].ts.
const API_BASE_URL = "/api/proxy";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
  } catch {
    throw new ApiError(0, "Could not reach the app. Check your connection.");
  }

  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body?.detail || JSON.stringify(body);
    } catch {
      detail = await res.text().catch(() => "");
    }
    throw new ApiError(res.status, detail || `Request to ${path} failed (${res.status})`);
  }

  return res.json() as Promise<T>;
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
