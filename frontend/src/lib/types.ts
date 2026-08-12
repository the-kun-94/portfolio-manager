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
export type TierName = "GROWTH" | "STABLE" | "HIGH_VOL";

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

  // True when live_price is a pre/post-market quote rather than the
  // regular-session close.
  is_after_hours: boolean;

  // Extended Trend — 50/200-day context + recent-move magnitude.
  // Informational only, never affects `signal`. sma200/pct_vs_200d/cross
  // are null for tickers with under 200 daily bars of history.
  sma50: number | null;
  sma200: number | null;
  pct_vs_50d: number | null;
  pct_vs_200d: number | null;
  cross: "GOLDEN" | "DEATH" | null;
  recent_move_pct: number | null;
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

export type StyleTiltLabel = "GROWTH_LEADING" | "VALUE_LEADING" | "NEUTRAL";

export interface ReinvestmentRecommendationOut {
  cash_balance: number;
  has_actionable_buy: boolean;
  actionable_buy_tickers: string[];
  recommended_etf: string;
  reason: string;

  // Growth/value style tilt — a leading indicator, informational only,
  // never changes recommended_etf. null when price data is unavailable.
  style_tilt: StyleTiltLabel | null;
  style_tilt_spread: number | null;
  style_tilt_note: string | null;
}

export interface ParkCashRequest {
  amount?: number;
  ticker?: string;
}

export interface UnparkRequest {
  ticker: string;
  shares?: number;
}
