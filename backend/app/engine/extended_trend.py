"""
Extended trend context — informational only, never a Dual-Gate input.

Surfaces the 50/200-day picture (the "is the longer trend actually broken"
question) plus a recent-move magnitude, so a weak 50/200-day read can be
told apart from a lag artifact sitting behind a genuine, fast move — this
is the LITE-vs-ORCL comparison from chat, formalized: a slow-moving
average naturally sits on the wrong side of a sharp recent move for a
while, and that's a very different situation from a modest bounce that
hasn't meaningfully dented a real prior decline.

Pure function, no I/O — the router passes in the same daily-close series
already fetched for the Dual-Gate pipeline, plus the live (possibly
after-hours) price used for display, so "recent move" reflects the
freshest price the user is actually looking at.
"""
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class ExtendedTrend:
    sma50: float
    sma200: Optional[float]        # None if <200 daily bars of history
    pct_vs_50d: float
    pct_vs_200d: Optional[float]
    cross: Optional[str]           # 'GOLDEN' | 'DEATH' | None (mirrors sma200)
    recent_move_pct: float         # current_price vs. price `lookback_days` bars ago


def compute_extended_trend(
    close_prices: pd.Series,
    current_price: float,
    recent_move_lookback_days: int,
) -> ExtendedTrend:
    sma50 = float(close_prices.rolling(window=50).mean().iloc[-1])
    pct_vs_50d = (current_price - sma50) / sma50 if sma50 > 0 else 0.0

    sma200: Optional[float] = None
    pct_vs_200d: Optional[float] = None
    cross: Optional[str] = None
    if len(close_prices) >= 200:
        sma200 = float(close_prices.rolling(window=200).mean().iloc[-1])
        pct_vs_200d = (current_price - sma200) / sma200 if sma200 > 0 else 0.0
        cross = "GOLDEN" if sma50 > sma200 else "DEATH"

    if len(close_prices) > recent_move_lookback_days:
        past_price = float(close_prices.iloc[-(recent_move_lookback_days + 1)])
        recent_move_pct = (current_price - past_price) / past_price if past_price > 0 else 0.0
    else:
        recent_move_pct = 0.0

    return ExtendedTrend(
        sma50=sma50,
        sma200=sma200,
        pct_vs_50d=pct_vs_50d,
        pct_vs_200d=pct_vs_200d,
        cross=cross,
        recent_move_pct=recent_move_pct,
    )
