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
from app.engine.data_fetcher import get_close_series
from app.engine.decision_engine import evaluate_holding

logger = logging.getLogger("emotionless_executioner.signals")

router = APIRouter(prefix="/api", tags=["decision-engine"])

# Signals that belong on the top-level Action Feed (excludes WAIT/RUN_WINNER,
# which are informational rather than "go do something right now").
ACTIONABLE_SIGNALS = {"BUY_DIP", "HARVEST", "EXIT_TRAILING_STOP", "EXIT_STOP_LOSS"}


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
        except ValueError as exc:
            # Bad/missing ticker data shouldn't take down the whole feed —
            # log it and skip that one row.
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

        results.append(schemas.SignalOut(**signal.__dict__))

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
    return schemas.SignalOut(**signal.__dict__)
