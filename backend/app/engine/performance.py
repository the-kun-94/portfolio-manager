"""
Portfolio performance vs. benchmark indices, from the account's first
recorded cash flow to today.

Renders one number per trading day: what a dollar that entered the
portfolio on the day it entered is worth now, here vs. in each benchmark.
Because contributions land at different times (an initial deposit, plus
whatever's added or pulled out later), a plain value or share-price-style
chart isn't a fair comparison — a $10k initial deposit that's since doubled
looks identical, on a raw value chart, to a $10k deposit made yesterday.
Instead every series is indexed by net external contributions to date:

    index(t) = total_value(t) / net_contributions(t)

`total_value(t)` is cash + the day's mark-to-market of every position held.
`net_contributions(t)` is the running sum of DEPOSIT minus WITHDRAWAL
cash-ledger entries only — BUY/SELL/PARK_ETF/UNPARK_ETF are internal
reallocations between cash and equity and net to zero on total value, so
they don't belong in the denominator.

The benchmark series replays the identical contribution schedule into a
hypothetical 100%-benchmark portfolio: each deposit buys that benchmark at
its closing price on the day the money arrived, each withdrawal sells the
same dollar amount. Both curves then share the same denominator at every
point in time, so `index(t) - 1` is a like-for-like comparison: "so far,
per dollar contributed, this portfolio vs. just buying the benchmark."

Pure function, no I/O — the router fetches transactions/cash-ledger rows
and price history and passes them in here.
"""
from dataclasses import dataclass
from typing import Optional

import pandas as pd

# Below this many dollars of net external contributions, value/contributions
# is undefined or too noisy to show — e.g. before the first deposit lands.
_MIN_CONTRIBUTIONS_FOR_INDEX = 1.0


@dataclass(frozen=True)
class TickerFlow:
    ticker: str
    date: pd.Timestamp
    signed_shares: float   # +shares on BUY, -shares on SELL


@dataclass(frozen=True)
class CashFlow:
    date: pd.Timestamp
    amount: float           # signed: positive = inflow, negative = outflow


@dataclass(frozen=True)
class PerformancePoint:
    date: pd.Timestamp
    portfolio_value: float
    portfolio_return_pct: Optional[float]
    benchmark_return_pct: dict[str, Optional[float]]


@dataclass(frozen=True)
class PerformanceHistory:
    points: list[PerformancePoint]
    net_contributions: float
    portfolio_return_pct: Optional[float]
    benchmark_return_pct: dict[str, Optional[float]]


_EMPTY = PerformanceHistory(points=[], net_contributions=0.0, portfolio_return_pct=None, benchmark_return_pct={})


def _cumulative_on_timeline(events: list[tuple[pd.Timestamp, float]], timeline: pd.DatetimeIndex) -> pd.Series:
    """Cumulative sum of signed `amount` events, stepped onto `timeline`
    (forward-filled, 0 before the first event)."""
    if not events or len(timeline) == 0:
        return pd.Series(0.0, index=timeline)
    by_date: dict[pd.Timestamp, float] = {}
    for date, amount in events:
        by_date[date] = by_date.get(date, 0.0) + amount
    stepped = pd.Series(by_date).sort_index().cumsum()
    return stepped.reindex(timeline, method="ffill").fillna(0.0)


def _price_at_or_before(close: pd.Series, date: pd.Timestamp) -> Optional[float]:
    """Last available close at or before `date`; None if `date` predates the
    series entirely."""
    value = close.asof(date)
    return None if pd.isna(value) else float(value)


def _index_pct(value: float, contributions: float) -> Optional[float]:
    if contributions < _MIN_CONTRIBUTIONS_FOR_INDEX:
        return None
    return (value / contributions) - 1.0


def compute_performance_history(
    ticker_flows: list[TickerFlow],
    all_cash_ledger: list[CashFlow],
    external_cash_flows: list[CashFlow],
    holding_close: dict[str, pd.Series],
    benchmark_close: dict[str, pd.Series],
    canonical_benchmark: str,
) -> PerformanceHistory:
    """
    `holding_close`/`benchmark_close` map ticker -> a tz-naive, midnight-
    normalized daily close Series (see data_fetcher.get_full_close_series).
    `canonical_benchmark` must be a key of `benchmark_close` — its trading
    calendar becomes the chart's timeline, since a broad-market benchmark is
    the one series guaranteed to have a full, gap-free daily history.
    """
    canonical_series = benchmark_close.get(canonical_benchmark)
    if canonical_series is None or canonical_series.empty:
        return _EMPTY

    all_dates = [f.date for f in ticker_flows] + [c.date for c in all_cash_ledger]
    if not all_dates:
        return _EMPTY
    start = min(all_dates)

    calendar = canonical_series.index
    timeline = calendar[calendar >= start]
    if len(timeline) == 0:
        return _EMPTY

    cash_balance = _cumulative_on_timeline([(c.date, c.amount) for c in all_cash_ledger], timeline)
    net_contributions = _cumulative_on_timeline([(c.date, c.amount) for c in external_cash_flows], timeline)

    tickers = sorted({f.ticker for f in ticker_flows})
    equity_value = pd.Series(0.0, index=timeline)
    for ticker in tickers:
        close = holding_close.get(ticker)
        if close is None or close.empty:
            continue
        flows = [(f.date, f.signed_shares) for f in ticker_flows if f.ticker == ticker]
        shares_held = _cumulative_on_timeline(flows, timeline)
        price = close.reindex(timeline, method="ffill").fillna(0.0)
        equity_value = equity_value.add(shares_held * price, fill_value=0.0)

    portfolio_value = cash_balance + equity_value

    benchmark_value: dict[str, pd.Series] = {}
    for bench_ticker, close in benchmark_close.items():
        shares = 0.0
        snapshots: dict[pd.Timestamp, float] = {}
        for flow in sorted(external_cash_flows, key=lambda c: c.date):
            price = _price_at_or_before(close, flow.date)
            if not price:
                continue
            shares += flow.amount / price
            snapshots[flow.date] = shares   # cumulative shares held as of this flow
        if snapshots:
            stepped = pd.Series(snapshots).sort_index()
            bench_shares = stepped.reindex(timeline, method="ffill").fillna(0.0)
        else:
            bench_shares = pd.Series(0.0, index=timeline)
        bench_price = close.reindex(timeline, method="ffill").fillna(0.0)
        benchmark_value[bench_ticker] = bench_shares * bench_price

    points: list[PerformancePoint] = []
    for date in timeline:
        contributions = float(net_contributions.loc[date])
        p_value = float(portfolio_value.loc[date])
        points.append(PerformancePoint(
            date=date,
            portfolio_value=p_value,
            portfolio_return_pct=_index_pct(p_value, contributions),
            benchmark_return_pct={
                ticker: _index_pct(float(series.loc[date]), contributions)
                for ticker, series in benchmark_value.items()
            },
        ))

    final_contributions = float(net_contributions.iloc[-1])
    return PerformanceHistory(
        points=points,
        net_contributions=final_contributions,
        portfolio_return_pct=_index_pct(float(portfolio_value.iloc[-1]), final_contributions),
        benchmark_return_pct={
            ticker: _index_pct(float(series.iloc[-1]), final_contributions)
            for ticker, series in benchmark_value.items()
        },
    )
