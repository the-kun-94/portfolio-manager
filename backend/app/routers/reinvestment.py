"""
Reinvestment Engine ("The Siphon") — routes idle cash into the strongest
Foundation ETF (or a broad-market default) when no active BUY_DIP signal is
already claiming it.

Execution is explicit, same manual-trigger pattern as /api/trades: this
module never moves money on its own, it only recommends and — on request —
logs a park/unpark trade through the same WAC/cash-ledger bookkeeping as
every other position.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, crud
from app.config import (
    FOUNDATION_ETFS,
    FOUNDATION_ETF_SECTOR_PROXY,
    DEFAULT_FOUNDATION_ETF,
    FOUNDATION_ETF_TIER,
)
from app.engine.data_fetcher import get_live_price
from app.engine.reinvestment import recommend_foundation_etf
from app.routers.signals import compute_sector_ranks, run_decision_engine

router = APIRouter(prefix="/api/reinvestment", tags=["reinvestment"])


def _actionable_buy_tickers(db: Session) -> list[str]:
    # Reuses the Decision Engine's own actionable-signal pass (and its
    # signal_log audit trail) rather than re-implementing per-holding
    # evaluation here — a BUY_DIP on an existing position always outranks
    # parking cash in a Foundation ETF.
    signals = run_decision_engine(only_actionable=True, db=db)
    return [s.ticker for s in signals if s.signal == "BUY_DIP"]


@router.get("/recommendation", response_model=schemas.ReinvestmentRecommendationOut)
def recommendation(db: Session = Depends(get_db)):
    cash_balance = crud.get_cash_balance(db)
    rec = recommend_foundation_etf(
        compute_sector_ranks(), FOUNDATION_ETF_SECTOR_PROXY, DEFAULT_FOUNDATION_ETF
    )
    buy_tickers = _actionable_buy_tickers(db)

    return schemas.ReinvestmentRecommendationOut(
        cash_balance=cash_balance,
        has_actionable_buy=bool(buy_tickers),
        actionable_buy_tickers=buy_tickers,
        recommended_etf=rec.etf_ticker,
        reason=rec.reason,
    )


@router.post("/park", response_model=schemas.TransactionOut, status_code=201)
def park_cash(body: schemas.ParkCashRequest, db: Session = Depends(get_db)):
    ticker = (
        body.ticker.upper()
        if body.ticker
        else recommend_foundation_etf(
            compute_sector_ranks(), FOUNDATION_ETF_SECTOR_PROXY, DEFAULT_FOUNDATION_ETF
        ).etf_ticker
    )
    if ticker not in FOUNDATION_ETFS:
        raise HTTPException(
            status_code=422,
            detail=f"'{ticker}' is not a configured Foundation ETF ({FOUNDATION_ETFS}).",
        )

    cash_balance = crud.get_cash_balance(db)
    amount = body.amount if body.amount is not None else cash_balance
    if amount <= 0:
        raise HTTPException(status_code=422, detail="No cash available to park.")
    if amount > cash_balance + 1e-9:
        raise HTTPException(
            status_code=422,
            detail=f"Requested {amount}, only {cash_balance:.2f} in cash available.",
        )

    try:
        live_price = get_live_price(ticker)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Live price unavailable for '{ticker}': {exc}")

    trade = schemas.TradeCreate(
        ticker=ticker,
        action="BUY",
        shares=amount / live_price,
        price=live_price,
        signal_type="PARK",
        notes="Parked by the Reinvestment Engine (The Siphon).",
        tier_name=FOUNDATION_ETF_TIER,
    )
    return crud.record_trade(db, trade, buy_entry_type="PARK_ETF")


@router.post("/unpark", response_model=schemas.TransactionOut, status_code=201)
def unpark_cash(body: schemas.UnparkRequest, db: Session = Depends(get_db)):
    ticker = body.ticker.upper()
    if ticker not in FOUNDATION_ETFS:
        raise HTTPException(
            status_code=422,
            detail=f"'{ticker}' is not a configured Foundation ETF ({FOUNDATION_ETFS}).",
        )

    holding = (
        db.query(models.Holding)
        .filter(models.Holding.ticker == ticker, models.Holding.is_active.is_(True))
        .one_or_none()
    )
    if holding is None:
        raise HTTPException(status_code=404, detail=f"No parked position open in '{ticker}'.")

    shares = body.shares if body.shares is not None else float(holding.shares)

    try:
        live_price = get_live_price(ticker)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Live price unavailable for '{ticker}': {exc}")

    trade = schemas.TradeCreate(
        ticker=ticker,
        action="SELL",
        shares=shares,
        price=live_price,
        signal_type="UNPARK",
        notes="Unparked by the Reinvestment Engine (The Siphon).",
    )
    try:
        return crud.record_trade(db, trade, sell_entry_type="UNPARK_ETF")
    except crud.InsufficientSharesError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
