"""Trade Execution UI backend."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_write_access
from app.database import get_db
from app import models, schemas, crud

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.post(
    "", response_model=schemas.TransactionOut, status_code=201,
    dependencies=[Depends(require_write_access)],
)
def create_trade(trade: schemas.TradeCreate, db: Session = Depends(get_db)):
    trade.ticker = trade.ticker.upper()
    try:
        txn = crud.record_trade(db, trade)
    except crud.InsufficientSharesError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except crud.UnknownTickerError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return txn


@router.get("/recent", response_model=list[schemas.TransactionOut])
def recent_trades(limit: int = 10, db: Session = Depends(get_db)):
    """Transaction History module — last N trades for audit purposes."""
    limit = max(1, min(limit, 100))
    return (
        db.query(models.Transaction)
        .order_by(models.Transaction.trade_date.desc())
        .limit(limit)
        .all()
    )
