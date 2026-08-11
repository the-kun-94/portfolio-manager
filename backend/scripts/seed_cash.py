"""
Seed a starting CASH balance — for money that's sitting in a cash-equivalent
vehicle rather than an actively-managed Dual-Gate position.

Why this exists: the original spec's Command Header explicitly separates
"Active Equity" from the "CASH/VTES Parking Lot" — i.e. a short-term
bond/money-market ETF like VTES is meant to be treated as cash, not run
through the 8/21-EMA momentum engine (its price barely moves, so Dual-Gate
buy/harvest/stop-loss thresholds would just be noise). `seed_from_csv.py`
is for real Dual-Gate holdings only; use this for that kind of balance
instead of adding it as a fake "position."

Usage:
    cd backend
    python -m scripts.seed_cash 8039.96 --notes "VTES parking lot balance, imported from brokerage"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, Base, engine  # noqa: E402
from app import crud  # noqa: E402


def seed_cash(amount: float, notes: str) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        entry = crud._write_cash_entry(
            db, "DEPOSIT", abs(amount), related_ticker=None, transaction_id=None, notes=notes
        )
        db.commit()
        print(f"Deposited ${amount:,.2f}. Cash ledger balance is now ${float(entry.balance_after):,.2f}.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("amount", type=float, help="Dollar amount to deposit into the cash ledger")
    parser.add_argument("--notes", default="Seeded starting cash balance", help="Note for the ledger entry")
    args = parser.parse_args()
    seed_cash(args.amount, args.notes)
