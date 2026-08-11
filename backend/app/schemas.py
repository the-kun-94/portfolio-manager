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


# ---------------------------------------------------------------------------
# Command Header
# ---------------------------------------------------------------------------
class CashSummary(BaseModel):
    cash_balance: float
    active_equity_value: float
    total_liquidity: float
