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
    FULL_HISTORY_CACHE_TTL_SECONDS,
)


@dataclass
class _CacheEntry:
    fetched_at: float
    data: pd.Series


@dataclass
class LiveQuote:
    price: float
    market_state: str        # Yahoo's own label: 'PRE', 'REGULAR', 'POST', 'POSTPOST', 'CLOSED', ...
    is_after_hours: bool      # True when `price` is a pre/post-market quote, not the regular-session price


@dataclass
class _QuoteCacheEntry:
    fetched_at: float
    quote: "LiveQuote"


_price_history_cache: dict[str, _CacheEntry] = {}
_quote_cache: dict[str, _QuoteCacheEntry] = {}


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


def get_live_quote(ticker: str, force_refresh: bool = False) -> LiveQuote:
    """
    Current tradeable price, preferring a pre/post-market quote over the
    regular-session close when the market is closed and Yahoo has one —
    this is what makes prices move on the dashboard outside 9:30-4:00 ET.

    Only the *displayed* price changes; EMA/high-water-mark math still runs
    off get_close_series's daily bars untouched, so a thin, volatile
    after-hours print never affects the actual BUY/SELL gate — see
    routers/signals.py for how the two are recombined.

    Cached same as get_close_series, to keep repeated dashboard polls cheap.
    """
    cached = _quote_cache.get(ticker)
    now = time.time()
    if not force_refresh and cached and (now - cached.fetched_at) < QUOTE_CACHE_TTL_SECONDS:
        return cached.quote

    try:
        info = yf.Ticker(ticker).info
    except Exception:
        info = {}

    market_state = info.get("marketState", "UNKNOWN")

    # Pick whichever price has the freshest timestamp, rather than matching
    # marketState strings — Yahoo reports more states than just PRE/REGULAR/
    # POST (e.g. PREPRE, the overnight gap after post-market ends and before
    # pre-market begins), and matching by name means silently falling back
    # to a stale regular-session price whenever a state isn't in the list.
    # postMarketPrice/postMarketTime stay populated with the prior session's
    # last print through that whole gap, so timestamp comparison picks it up
    # correctly regardless of what marketState says.
    candidates: list[tuple[str, float, int]] = []
    for session, price_key, time_key in (
        ("regular", "regularMarketPrice", "regularMarketTime"),
        ("post", "postMarketPrice", "postMarketTime"),
        ("pre", "preMarketPrice", "preMarketTime"),
    ):
        price_val = info.get(price_key)
        time_val = info.get(time_key)
        if price_val is not None and time_val is not None:
            candidates.append((session, float(price_val), int(time_val)))

    if candidates:
        session, price, _ts = max(candidates, key=lambda c: c[2])
        is_ah = session != "regular"
    else:
        # Quote snapshot had nothing usable — fall back to the last daily close.
        price, is_ah = float(get_close_series(ticker).iloc[-1]), False

    quote = LiveQuote(price=price, market_state=market_state, is_after_hours=is_ah)
    _quote_cache[ticker] = _QuoteCacheEntry(fetched_at=now, quote=quote)
    return quote


def get_live_price(ticker: str) -> float:
    """Current tradeable price — see get_live_quote for the after-hours logic."""
    return get_live_quote(ticker).price


_full_history_cache: dict[str, _CacheEntry] = {}


def get_full_close_series(ticker: str, force_refresh: bool = False) -> pd.Series:
    """
    Full available daily-close history for `ticker` (period="max"), tz-naive
    and normalized to midnight so it can be reindexed against dates pulled
    straight from the database. Used by the performance-vs-benchmark chart,
    which needs history back to the portfolio's inception rather than the
    rolling window get_close_series keeps for the Decision Engine — cached
    separately (and longer) so the two caches can't thrash each other.
    """
    cached = _full_history_cache.get(ticker)
    now = time.time()
    if not force_refresh and cached and (now - cached.fetched_at) < FULL_HISTORY_CACHE_TTL_SECONDS:
        return cached.data

    history = yf.Ticker(ticker).history(period="max", interval="1d", auto_adjust=True)
    if history.empty:
        raise ValueError(f"yfinance returned no price history for '{ticker}'")

    close_series = history["Close"].dropna()
    close_series.index = close_series.index.tz_localize(None).normalize()
    _full_history_cache[ticker] = _CacheEntry(fetched_at=now, data=close_series)
    return close_series
