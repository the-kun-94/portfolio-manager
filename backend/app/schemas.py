"""Pydantic request/response models for the API layer."""
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Trade Execution UI
# ---------------------------------------------------------------------------
class TradeCreate(BaseModel):
    ticker: str
    action: Literal["BUY", "SELL"]
    shares: float = Field(gt=0)
    price: float = Field(gt=0)
    signal_type: Optional[str] = "MANUAL"
    notes: Optional[str] = None
    tier_name: Optional[Literal["GROWTH", "STABLE"]] = None  # required only for a brand-new ticker


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    action: str
    shares: float
    price: float
    trade_date: datetime
    signal_type: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Dual-Gate Ledger
# ---------------------------------------------------------------------------
class HoldingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    tier_name: str
    shares: float
    wac: float
    high_water_mark: Optional[float] = None
    is_active: bool


# ---------------------------------------------------------------------------
# Decision Engine
# ---------------------------------------------------------------------------
class SignalOut(BaseModel):
    ticker: str
    tier: str
    live_price: float
    shares: float
    wac: float
    high_water_mark: Optional[float]
    roi_pct: float
    is_legacy_winner: bool
    anchor_type: Literal["WAC", "HIGH_WATER_MARK"]
    anchor_price: float
    pct_from_anchor: float
    ema8: float
    ema21: float
    trend: Literal["UP", "DN"]
    signal: Literal[
        "BUY_DIP", "RUN_WINNER", "HARVEST",
        "EXIT_TRAILING_STOP", "EXIT_STOP_LOSS", "WAIT",
    ]
    suggested_sell_pct: Optional[float] = None
    label: str            # human-readable, emoji-prefixed for the Action Feed
    reason: str            # one-line explanation of why the signal fired

    # Sector Relative Strength — informational only, does not affect `signal`.
    # None for tickers with no mapped sector (e.g. broad-market/bond ETFs).
    sector_label: Optional[str] = None
    sector_rank: Optional[int] = None
    sector_relative_strength: Optional[float] = None


# ---------------------------------------------------------------------------
# Sector Relative Strength leaderboard
# ---------------------------------------------------------------------------
class SectorRankOut(BaseModel):
    etf_ticker: str
    sector_label: str
    relative_strength: float
    rank: int


# ---------------------------------------------------------------------------
# Command Header
# ---------------------------------------------------------------------------
class CashSummary(BaseModel):
    cash_balance: float
    active_equity_value: float
    total_liquidity: float


# ---------------------------------------------------------------------------
# Reinvestment Engine ("The Siphon")
# ---------------------------------------------------------------------------
class ReinvestmentRecommendationOut(BaseModel):
    cash_balance: float
    has_actionable_buy: bool               # True if a real BUY_DIP already wants this cash
    actionable_buy_tickers: list[str]
    recommended_etf: str
    reason: str

    # Growth/value style tilt — a leading indicator, informational only,
    # never changes `recommended_etf`. None when price data is unavailable.
    style_tilt: Optional[Literal["GROWTH_LEADING", "VALUE_LEADING", "NEUTRAL"]] = None
    style_tilt_spread: Optional[float] = None
    style_tilt_note: Optional[str] = None  # set only when the tilt is worth a second look


class ParkCashRequest(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)   # omit to park the full cash balance
    ticker: Optional[str] = None                            # omit to use the recommended ETF


class UnparkRequest(BaseModel):
    ticker: str
    shares: Optional[float] = Field(default=None, gt=0)   # omit to sell the entire parked position
