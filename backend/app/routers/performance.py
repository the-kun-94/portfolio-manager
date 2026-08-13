"""Performance-vs-benchmark chart backend — GET /api/performance/history."""
import logging

import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.config import PERFORMANCE_BENCHMARKS
from app.engine.data_fetcher import get_full_close_series
from app.engine.performance import CashFlow, TickerFlow, compute_performance_history

router = APIRouter(prefix="/api/performance", tags=["performance"])
logger = logging.getLogger("the_kun_algorithm.performance")

_EXTERNAL_CASH_ENTRY_TYPES = {"DEPOSIT", "WITHDRAWAL"}
_EMPTY_RESPONSE_KWARGS = {"points": [], "net_contributions": 0.0, "benchmark_labels": PERFORMANCE_BENCHMARKS}


@router.get("/history", response_model=schemas.PerformanceHistoryOut)
def performance_history(db: Session = Depends(get_db)):
    """
    Portfolio return, indexed by net external contributions to date, vs. the
    same contribution schedule replayed into each configured benchmark —
    see engine/performance.py for the full methodology.
    """
    transactions = db.query(models.Transaction).order_by(models.Transaction.trade_date).all()
    cash_ledger = db.query(models.CashLedgerEntry).order_by(models.CashLedgerEntry.created_at).all()

    if not transactions and not cash_ledger:
        return schemas.PerformanceHistoryOut(**_EMPTY_RESPONSE_KWARGS)

    ticker_flows = [
        TickerFlow(
            ticker=t.ticker,
            date=pd.Timestamp(t.trade_date).normalize(),
            signed_shares=float(t.shares) if t.action == "BUY" else -float(t.shares),
        )
        for t in transactions
    ]
    all_cash_flows = [
        CashFlow(date=pd.Timestamp(c.created_at).normalize(), amount=float(c.amount))
        for c in cash_ledger
    ]
    external_cash_flows = [
        flow for flow, c in zip(all_cash_flows, cash_ledger)
        if c.entry_type in _EXTERNAL_CASH_ENTRY_TYPES
    ]

    holding_close: dict[str, pd.Series] = {}
    for ticker in sorted({t.ticker for t in transactions}):
        try:
            holding_close[ticker] = get_full_close_series(ticker)
        except Exception as exc:
            logger.warning("Performance chart: skipping %s, no price history: %s", ticker, exc)

    benchmark_close: dict[str, pd.Series] = {}
    for ticker in PERFORMANCE_BENCHMARKS:
        try:
            benchmark_close[ticker] = get_full_close_series(ticker)
        except Exception as exc:
            logger.warning("Performance chart: benchmark %s unavailable: %s", ticker, exc)

    if not benchmark_close:
        return schemas.PerformanceHistoryOut(**_EMPTY_RESPONSE_KWARGS)

    canonical_benchmark = next(iter(benchmark_close))
    history = compute_performance_history(
        ticker_flows=ticker_flows,
        all_cash_ledger=all_cash_flows,
        external_cash_flows=external_cash_flows,
        holding_close=holding_close,
        benchmark_close=benchmark_close,
        canonical_benchmark=canonical_benchmark,
    )

    return schemas.PerformanceHistoryOut(
        points=[
            schemas.PerformancePointOut(
                date=p.date.strftime("%Y-%m-%d"),
                portfolio_value=p.portfolio_value,
                portfolio_return_pct=p.portfolio_return_pct,
                benchmark_return_pct=p.benchmark_return_pct,
            )
            for p in history.points
        ],
        net_contributions=history.net_contributions,
        portfolio_return_pct=history.portfolio_return_pct,
        benchmark_return_pct=history.benchmark_return_pct,
        benchmark_labels=PERFORMANCE_BENCHMARKS,
    )
