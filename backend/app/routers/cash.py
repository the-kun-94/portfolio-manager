"""Manual cash ledger adjustments (deposits/withdrawals) — everything else
(SALE_PROCEEDS/BUY_DEBIT) is posted automatically by crud.record_trade."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, crud

router = APIRouter(prefix="/api/cash", tags=["cash"])


@router.post("/deposit")
def deposit_cash(amount: float, notes: str = "", db: Session = Depends(get_db)):
    entry = crud._write_cash_entry(db, "DEPOSIT", abs(amount), None, None, notes)
    db.commit()
    return {"balance_after": float(entry.balance_after)}


@router.post("/withdraw")
def withdraw_cash(amount: float, notes: str = "", db: Session = Depends(get_db)):
    entry = crud._write_cash_entry(db, "WITHDRAWAL", -abs(amount), None, None, notes)
    db.commit()
    return {"balance_after": float(entry.balance_after)}


@router.get("/ledger")
def recent_cash_ledger(limit: int = 20, db: Session = Depends(get_db)):
    limit = max(1, min(limit, 200))
    entries = (
        db.query(models.CashLedgerEntry)
        .order_by(models.CashLedgerEntry.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "entry_type": e.entry_type,
            "amount": float(e.amount),
            "balance_after": float(e.balance_after),
            "related_ticker": e.related_ticker,
            "notes": e.notes,
            "created_at": e.created_at,
        }
        for e in entries
    ]
