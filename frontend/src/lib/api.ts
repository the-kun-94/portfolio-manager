import type {
  SignalOut,
  HoldingOut,
  TransactionOut,
  CashSummary,
  TradeCreate,
} from "./types";

// Set in .env.local for dev, or as a Vercel Environment Variable for prod.
// Falls back to a local backend so `npm run dev` works with zero config.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

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
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError(0, `Could not reach the Engine at ${API_BASE_URL}. Is it running?`);
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

  createTrade: (trade: TradeCreate) =>
    request<TransactionOut>("/api/trades", {
      method: "POST",
      body: JSON.stringify(trade),
    }),
};

export { ApiError };
