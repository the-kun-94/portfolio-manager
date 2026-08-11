"""
Technical indicators — Gate 2 of the Dual-Gate Momentum Engine.

Kept dependency-light (pandas only) and pure: functions take a price series
in, return numbers/series out, no I/O. Makes this trivially unit-testable
without mocking yfinance.
"""
from dataclasses import dataclass

import pandas as pd

from app.config import EMA_FAST_SPAN, EMA_SLOW_SPAN


def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average, adjust=False to match standard charting
    platforms (TradingView/thinkorswim) bar-for-bar."""
    return series.ewm(span=span, adjust=False).mean()


@dataclass(frozen=True)
class MomentumState:
    ema_fast: float     # 8-day EMA, most recent close
    ema_slow: float      # 21-day EMA, most recent close
    trend: str            # 'UP' | 'DN'


def compute_momentum(close_prices: pd.Series) -> MomentumState:
    """
    Gate 2: compares the 8-day EMA to the 21-day EMA on the latest bar.

    8-EMA > 21-EMA -> Trend UP  (Confirmed Momentum)
    8-EMA < 21-EMA -> Trend DN  (Momentum Broken)

    Ties (rare with floats) resolve to DN — the rulebook says "never buy a
    stock if the trend is DN, even if it hits the price target," so the
    stricter reading wins on ambiguity.
    """
    if len(close_prices) < EMA_SLOW_SPAN:
        raise ValueError(
            f"Need at least {EMA_SLOW_SPAN} bars to compute a stable 21-EMA; "
            f"got {len(close_prices)}."
        )

    ema_fast_series = ema(close_prices, EMA_FAST_SPAN)
    ema_slow_series = ema(close_prices, EMA_SLOW_SPAN)

    ema_fast_latest = float(ema_fast_series.iloc[-1])
    ema_slow_latest = float(ema_slow_series.iloc[-1])
    trend = "UP" if ema_fast_latest > ema_slow_latest else "DN"

    return MomentumState(ema_fast=ema_fast_latest, ema_slow=ema_slow_latest, trend=trend)


def high_water_mark(close_prices: pd.Series, lookback_days: int) -> tuple[float, pd.Timestamp]:
    """Peak closing price (and the date it occurred) over the trailing window."""
    window = close_prices.tail(lookback_days)
    peak_price = float(window.max())
    peak_date = window.idxmax()
    return peak_price, peak_date
