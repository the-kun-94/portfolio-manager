"""
Sector Relative Strength — informational context, never a Dual-Gate input.

Ranks the 11 standard SPDR sector ETFs by how much they've out/underperformed
a broad-market benchmark over a trailing window. Answers a different question
than the Decision Engine does: not "should I act on this position" but "is
this stock's move sector-wide, or stock-specific."

Pure function core, same split as indicators.py — no I/O here; the router
fetches price history via data_fetcher and passes it in.
"""
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SectorRank:
    etf_ticker: str
    sector_label: str
    relative_strength: float   # sector ETF's return minus benchmark's return, over the window
    rank: int                   # 1 = strongest


def _period_return(close_prices: pd.Series, lookback_days: int) -> float:
    window = close_prices.tail(lookback_days + 1)
    if len(window) < 2:
        raise ValueError("Not enough price history to compute a period return.")
    start, end = float(window.iloc[0]), float(window.iloc[-1])
    return (end - start) / start


def rank_sectors(
    sector_close_series: dict[str, pd.Series],
    sector_labels: dict[str, str],
    benchmark_close: pd.Series,
    lookback_days: int,
) -> list[SectorRank]:
    """
    `sector_close_series` should only contain tickers whose price history
    fetched successfully — the caller is responsible for skipping failures,
    same pattern the Decision Engine router uses for individual holdings.
    """
    benchmark_return = _period_return(benchmark_close, lookback_days)

    scored: list[tuple[str, float]] = []
    for etf_ticker, close_series in sector_close_series.items():
        try:
            etf_return = _period_return(close_series, lookback_days)
        except ValueError:
            continue
        scored.append((etf_ticker, etf_return - benchmark_return))

    scored.sort(key=lambda pair: pair[1], reverse=True)

    return [
        SectorRank(
            etf_ticker=etf_ticker,
            sector_label=sector_labels.get(etf_ticker, etf_ticker),
            relative_strength=rs,
            rank=i + 1,
        )
        for i, (etf_ticker, rs) in enumerate(scored)
    ]
