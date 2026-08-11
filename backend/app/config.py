"""
Central configuration for The Kun Algorithm.

Every threshold the strategy depends on lives here — not scattered through
the engine — so the rulebook can be audited (and tuned) in one place without
touching decision logic.
"""
import os
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Defaults to a local SQLite file for zero-config dev. Point DATABASE_URL at
# Postgres in production, e.g.:
#   postgresql+psycopg2://user:pass@localhost:5432/the_kun_algorithm
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./the_kun_algorithm.db")
# Render/Heroku-style Postgres URLs are handed out as "postgres://" — SQLAlchemy
# 2.x + psycopg2 require the "postgresql://" scheme, so normalize it here once
# rather than making every deploy target remember to do it.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ---------------------------------------------------------------------------
# CORS — comma-separated list of allowed frontend origins. Defaults cover
# local Next.js dev; add your deployed Vercel URL (e.g.
# "https://emotionless-executioner.vercel.app") via this env var in prod —
# never widen this to "*" once real trade data is flowing through the API.
# ---------------------------------------------------------------------------
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

# Shared API key required on every endpoint except /api/health — this app
# has no login system, so this is what stops a stranger with the URL from
# reading or writing your data. Unset (empty) in local dev disables the
# check; set it in production. See app/auth.py.
API_KEY = os.getenv("API_KEY", "")


# ---------------------------------------------------------------------------
# Tier rules — mirrors the `tiers` table (DB is the source of truth at
# runtime; these are the fallback/seed values and are used by tests).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TierConfig:
    buy_trigger_pct: float      # negative: discount from anchor that triggers a BUY DIP
    harvest_target_pct: float   # positive: gain from anchor that triggers HARVEST evaluation
    stop_loss_pct: float        # negative: loss from cost basis (WAC) that triggers STOP LOSS


TIER_CONFIG: dict[str, TierConfig] = {
    "GROWTH": TierConfig(buy_trigger_pct=-0.10, harvest_target_pct=0.15, stop_loss_pct=-0.15),
    "STABLE": TierConfig(buy_trigger_pct=-0.05, harvest_target_pct=0.10, stop_loss_pct=-0.08),
}


# ---------------------------------------------------------------------------
# Hybrid Anchoring
# ---------------------------------------------------------------------------
LEGACY_WINNER_ROI_THRESHOLD = 0.50      # ROI above which anchor shifts WAC -> High-Water Mark
HIGH_WATER_MARK_LOOKBACK_DAYS = 180     # 6-month peak-close lookback window

# Legacy Winner trailing exit: sell 50% if price drops this far off the peak
# AND momentum (Gate 2) has flipped DN. Blueprint specifies an 8-10% band —
# we use the midpoint as the hard trigger; expose both bounds for tuning/UI.
TRAILING_STOP_MIN_PCT = -0.08
TRAILING_STOP_MAX_PCT = -0.10
TRAILING_STOP_TRIGGER_PCT = -0.08       # trigger as soon as the drop reaches -8%

# ---------------------------------------------------------------------------
# Position sizing on exits (fraction of current shares to sell)
# ---------------------------------------------------------------------------
HARVEST_SELL_FRACTION = 0.25            # 💰 HARVEST: trim 25% on target-hit + trend break
EXIT_TRAILING_SELL_FRACTION = 0.50      # 💰 EXIT / Trailing Stop: sell 50% (Legacy Winners)
EXIT_STOP_LOSS_SELL_FRACTION = 1.00     # 🛑 EXIT / Stop Loss: full exit (Standard positions)

# ---------------------------------------------------------------------------
# Momentum engine (Dual-Gate, Gate 2)
# ---------------------------------------------------------------------------
EMA_FAST_SPAN = 8
EMA_SLOW_SPAN = 21

# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------
PRICE_HISTORY_PERIOD = "1y"   # enough bars to warm up EMA-21 and compute the 6mo HWM
PRICE_HISTORY_INTERVAL = "1d"
QUOTE_CACHE_TTL_SECONDS = 60  # avoid hammering yfinance on repeated dashboard polls

# ---------------------------------------------------------------------------
# Reinvestment Engine ("The Siphon")
# ---------------------------------------------------------------------------
FOUNDATION_ETFS = ["VOO", "SMH"]   # parking lot when no active BUY signal wins the cash
DEFAULT_FOUNDATION_ETF = "VOO"     # broad-market fallback when no sector proxy qualifies
FOUNDATION_ETF_TIER = "STABLE"     # tier assigned to new parking-lot positions opened by the Siphon

# Foundation ETFs that track a single sector get first claim on parked cash
# when that sector is both the #1-ranked SPDR sector (by trailing RS vs. SPY)
# and still outperforming the benchmark outright. Anything not listed here
# (e.g. VOO) is sector-agnostic and only used as the DEFAULT_FOUNDATION_ETF
# fallback.
FOUNDATION_ETF_SECTOR_PROXY: dict[str, str] = {
    "SMH": "Technology",
}

# ---------------------------------------------------------------------------
# Style Rotation tilt — a leading indicator surfaced next to the
# Reinvestment Engine's recommendation, never a trigger on its own. The
# sector-RS rank above is a confirming signal computed over a 63-day
# window; by the time a sector clears that bar the rotation into it is
# often already underway. Growth-vs-value spread is a faster-moving proxy
# for the same rotation, so a shorter window here can flag "this pick may
# be running out of room" (or "there may be more room than the trailing
# number shows") before the sector-RS number catches up.
# ---------------------------------------------------------------------------
STYLE_GROWTH_ETF = "VUG"
STYLE_VALUE_ETF = "VTV"
STYLE_TILT_LOOKBACK_DAYS = 21     # ~1 trading month — shorter than SECTOR_RS_LOOKBACK_DAYS on purpose
STYLE_TILT_NEUTRAL_BAND = 0.01    # spread within +/-1% reads as NEUTRAL rather than a lean

# ---------------------------------------------------------------------------
# Sector Relative Strength — informational context only, never a Dual-Gate
# input. Ranks the 11 standard SPDR sector ETFs against a broad-market
# benchmark over a trailing window, so a holding's drawdown can be read as
# "the whole sector is down" vs. "this stock specifically is down."
# ---------------------------------------------------------------------------
SECTOR_RS_BENCHMARK = "SPY"
SECTOR_RS_LOOKBACK_DAYS = 63   # ~3 trading months

SECTOR_ETFS: dict[str, str] = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLC": "Communication Services",
}

# Best-effort ticker -> sector label for showing each holding's sector rank
# next to it. Unmapped tickers (e.g. broad-market/bond ETFs like VOO, VTES)
# just skip that column — there's no meaningful single sector for them.
TICKER_SECTOR_MAP: dict[str, str] = {
    "AMD": "Technology",
    "NVDA": "Technology",
    "AMAT": "Technology",
    "SMH": "Technology",
    "XLK": "Technology",
    "TGT": "Consumer Discretionary",
    "SONY": "Consumer Discretionary",
    "O": "Real Estate",
    "GOOG": "Communication Services",
    "ORCL": "Technology",
    "NOW": "Technology",
    "TEL": "Industrials",
    "LITE": "Technology",
    "RKLB": "Industrials",
    "AAOI": "Technology",
}
