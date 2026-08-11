"""
Market data access via yfinance, isolated behind a thin cache so the
Decision Engine (and a dashboard polling every few seconds) doesn't hammer
Yahoo's endpoints or trip rate limits.
"""
import time
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

from app.config import (
    PRICE_HISTORY_PERIOD,
    PRICE_HISTORY_INTERVAL,
    QUOTE_CACHE_TTL_SECONDS,
)


@dataclass
class _CacheEntry:
    fetched_at: float
    data: pd.Series


_price_history_cache: dict[str, _CacheEntry] = {}


def get_close_series(ticker: str, force_refresh: bool = False) -> pd.Series:
    """
    Returns a date-indexed Series of daily closes for `ticker`, long enough
    to warm up the 21-EMA and compute a 6-month high-water mark.

    Cached in-process for QUOTE_CACHE_TTL_SECONDS to keep repeated Decision
    Engine calls (e.g. dashboard auto-refresh) cheap and rate-limit-safe.
    """
    cached = _price_history_cache.get(ticker)
    now = time.time()
    if not force_refresh and cached and (now - cached.fetched_at) < QUOTE_CACHE_TTL_SECONDS:
        return cached.data

    history = yf.Ticker(ticker).history(
        period=PRICE_HISTORY_PERIOD,
        interval=PRICE_HISTORY_INTERVAL,
        auto_adjust=True,
    )
    if history.empty:
        raise ValueError(f"yfinance returned no price history for '{ticker}'")

    close_series = history["Close"].dropna()
    _price_history_cache[ticker] = _CacheEntry(fetched_at=now, data=close_series)
    return close_series


def get_live_price(ticker: str) -> float:
    """Most recent available close — 'live' at daily granularity.
    Swap the interval to '1h'/'5m' in config for intraday polling."""
    return float(get_close_series(ticker).iloc[-1])
