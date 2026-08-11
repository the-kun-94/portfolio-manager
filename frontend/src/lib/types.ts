// Mirrors backend/app/schemas.py — keep these in sync if the API changes.

export type SignalType =
  | "BUY_DIP"
  | "RUN_WINNER"
  | "HARVEST"
  | "EXIT_TRAILING_STOP"
  | "EXIT_STOP_LOSS"
  | "WAIT";

export type Trend = "UP" | "DN";
export type AnchorType = "WAC" | "HIGH_WATER_MARK";
export type TierName = "GROWTH" | "STABLE";

export interface SignalOut {
  ticker: string;
  tier: string;
  live_price: number;
  shares: number;
  wac: number;
  high_water_mark: number | null;
  roi_pct: number;
  is_legacy_winner: boolean;
  anchor_type: AnchorType;
  anchor_price: number;
  pct_from_anchor: number;
  ema8: number;
  ema21: number;
  trend: Trend;
  signal: SignalType;
  suggested_sell_pct: number | null;
  label: string;
  reason: string;

  // Sector Relative Strength — informational only, never affects `signal`.
  sector_label: string | null;
  sector_rank: number | null;
  sector_relative_strength: number | null;
}

export interface SectorRankOut {
  etf_ticker: string;
  sector_label: string;
  relative_strength: number;
  rank: number;
}

export interface HoldingOut {
  ticker: string;
  tier_name: string;
  shares: number;
  wac: number;
  high_water_mark: number | null;
  is_active: boolean;
}

export interface TransactionOut {
  id: number;
  ticker: string;
  action: "BUY" | "SELL";
  shares: number;
  price: number;
  trade_date: string;
  signal_type?: string | null;
  notes?: string | null;
}

export interface CashSummary {
  cash_balance: number;
  active_equity_value: number;
  total_liquidity: number;
}

export interface TradeCreate {
  ticker: string;
  action: "BUY" | "SELL";
  shares: number;
  price: number;
  signal_type?: string;
  notes?: string;
  tier_name?: TierName;
}

export interface ReinvestmentRecommendationOut {
  cash_balance: number;
  has_actionable_buy: boolean;
  actionable_buy_tickers: string[];
  recommended_etf: string;
  reason: string;
}

export interface ParkCashRequest {
  amount?: number;
  ticker?: string;
}

export interface UnparkRequest {
  ticker: string;
  shares?: number;
}
