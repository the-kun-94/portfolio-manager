"""
The Action Feed's data source. GET /api/decision-engine is the single
endpoint the frontend polls to render both the Action Feed (filtered to
actionable signals) and the per-row Signal Status column of the Dual-Gate
Ledger.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.config import (
    SECTOR_ETFS,
    SECTOR_RS_BENCHMARK,
    SECTOR_RS_LOOKBACK_DAYS,
    TICKER_SECTOR_MAP,
)
from app.engine.data_fetcher import get_close_series
from app.engine.decision_engine import evaluate_holding
from app.engine.sector_strength import SectorRank, rank_sectors

logger = logging.getLogger("the_kun_algorithm.signals")

router = APIRouter(prefix="/api", tags=["decision-engine"])

# Signals that belong on the top-level Action Feed (excludes WAIT/RUN_WINNER,
# which are informational rather than "go do something right now").
ACTIONABLE_SIGNALS = {"BUY_DIP", "HARVEST", "EXIT_TRAILING_STOP", "EXIT_STOP_LOSS"}


def compute_sector_ranks() -> list[SectorRank]:
    # Broad `except Exception`, not just ValueError — this runs once before
    # the holdings loop in run_decision_engine, so an uncaught exception here
    # (rate limit, network error — anything yfinance can throw) would crash
    # the entire /api/decision-engine call, not just the sector data.
    try:
        benchmark_close = get_close_series(SECTOR_RS_BENCHMARK)
    except Exception as exc:
        logger.warning("Sector strength unavailable: benchmark %s failed: %s", SECTOR_RS_BENCHMARK, exc)
        return []

    sector_close_series = {}
    for etf_ticker in SECTOR_ETFS:
        try:
            sector_close_series[etf_ticker] = get_close_series(etf_ticker)
        except Exception as exc:
            logger.warning("Skipping sector ETF %s: %s", etf_ticker, exc)

    return rank_sectors(sector_close_series, SECTOR_ETFS, benchmark_close, SECTOR_RS_LOOKBACK_DAYS)


@router.get("/sector-strength", response_model=list[schemas.SectorRankOut])
def sector_strength(db: Session = Depends(get_db)):
    """
    The 11 standard SPDR sector ETFs ranked by trailing relative strength
    vs. SPY. Each call is logged to `sector_strength` for the audit trail,
    same pattern as `signal_log` below.
    """
    ranks = compute_sector_ranks()

    for r in ranks:
        db.add(models.SectorStrength(
            etf_ticker=r.etf_ticker,
            sector_label=r.sector_label,
            relative_strength=r.relative_strength,
            rank=r.rank,
        ))
    db.commit()

    return [schemas.SectorRankOut(**r.__dict__) for r in ranks]


@router.get("/decision-engine", response_model=list[schemas.SignalOut])
def run_decision_engine(
    only_actionable: bool = False,
    db: Session = Depends(get_db),
):
    """
    Evaluates every active holding through the Dual-Gate + Hybrid Anchoring
    pipeline and returns one Signal per ticker. Also persists each result to
    signal_log for the audit trail.

    Set only_actionable=true to get just what the Action Feed needs
    (🟢 BUY / 💰 HARVEST / 💰 EXIT / 🛑 EXIT) — everything else stays WAIT
    or RUN_WINNER noise filtered out.
    """
    holdings = db.query(models.Holding).filter(models.Holding.is_active.is_(True)).all()

    # Computed once per call, not persisted here — informational context for
    # each row below, not a Dual-Gate input. GET /api/sector-strength is the
    # endpoint that logs the audit trail.
    sector_by_label = {r.sector_label: r for r in compute_sector_ranks()}

    results: list[schemas.SignalOut] = []
    for holding in holdings:
        try:
            close_series = get_close_series(holding.ticker)
            signal = evaluate_holding(
                ticker=holding.ticker,
                tier_name=holding.tier_name,
                shares=float(holding.shares),
                wac=float(holding.wac),
                close_prices=close_series,
            )
        except Exception as exc:
            # Bad/missing ticker data (or any other live-data failure —
            # rate limit, network error) shouldn't take down the whole
            # feed — log it and skip that one row.
            logger.warning("Skipping %s: %s", holding.ticker, exc)
            continue

        # Audit trail: every evaluation is logged, not just the ones that fire.
        db.add(models.SignalLog(
            ticker=signal.ticker,
            signal_type=signal.signal,
            price_at_signal=signal.live_price,
            anchor_price=signal.anchor_price,
            anchor_type=signal.anchor_type,
            pct_from_anchor=signal.pct_from_anchor,
            ema8=signal.ema8,
            ema21=signal.ema21,
            trend=signal.trend,
            suggested_sell_pct=signal.suggested_sell_pct,
        ))

        # Keep the cached high-water mark on the holding row current so the
        # ledger UI can show it without recomputing on every render.
        holding.high_water_mark = signal.high_water_mark

        sector_label = TICKER_SECTOR_MAP.get(holding.ticker)
        sector_rank_info = sector_by_label.get(sector_label) if sector_label else None

        results.append(schemas.SignalOut(
            **signal.__dict__,
            sector_label=sector_label,
            sector_rank=sector_rank_info.rank if sector_rank_info else None,
            sector_relative_strength=sector_rank_info.relative_strength if sector_rank_info else None,
        ))

    db.commit()

    if only_actionable:
        results = [r for r in results if r.signal in ACTIONABLE_SIGNALS]

    return results


@router.get("/decision-engine/{ticker}", response_model=schemas.SignalOut)
def run_decision_engine_for_ticker(ticker: str, db: Session = Depends(get_db)):
    holding = db.query(models.Holding).filter(models.Holding.ticker == ticker.upper()).one_or_none()
    if holding is None:
        raise HTTPException(status_code=404, detail=f"No holding found for '{ticker}'")

    close_series = get_close_series(holding.ticker)
    signal = evaluate_holding(
        ticker=holding.ticker,
        tier_name=holding.tier_name,
        shares=float(holding.shares),
        wac=float(holding.wac),
        close_prices=close_series,
    )

    sector_label = TICKER_SECTOR_MAP.get(holding.ticker)
    sector_rank_info = None
    if sector_label:
        sector_rank_info = next(
            (r for r in compute_sector_ranks() if r.sector_label == sector_label), None
        )

    return schemas.SignalOut(
        **signal.__dict__,
        sector_label=sector_label,
        sector_rank=sector_rank_info.rank if sector_rank_info else None,
        sector_relative_strength=sector_rank_info.relative_strength if sector_rank_info else None,
    )
