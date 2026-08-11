"""Dual-Gate Ledger + Command Header backend."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, crud
from app.engine.data_fetcher import get_live_price

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.get("/holdings", response_model=list[schemas.HoldingOut])
def list_holdings(include_inactive: bool = False, db: Session = Depends(get_db)):
    query = db.query(models.Holding)
    if not include_inactive:
        query = query.filter(models.Holding.is_active.is_(True))
    return query.order_by(models.Holding.ticker).all()


@router.get("/cash-summary", response_model=schemas.CashSummary)
def cash_summary(db: Session = Depends(get_db)):
    """
    Command Header data: total liquidity split into Active Equity (live
    mark-to-market of every open position) vs. the CASH/parking-lot balance.
    """
    cash_balance = crud.get_cash_balance(db)

    active_equity_value = 0.0
    holdings = db.query(models.Holding).filter(models.Holding.is_active.is_(True)).all()
    for holding in holdings:
        try:
            live_price = get_live_price(holding.ticker)
        except ValueError:
            live_price = float(holding.wac)  # fall back to cost basis if data fetch fails
        active_equity_value += live_price * float(holding.shares)

    return schemas.CashSummary(
        cash_balance=cash_balance,
        active_equity_value=active_equity_value,
        total_liquidity=cash_balance + active_equity_value,
    )
