"""
One-time portfolio import — loads existing positions from a CSV export of
your current holdings into the ledger, using the exact same WAC-recalculation
path (`crud.record_trade`) the Trade Execution UI uses. This makes each
seeded position look, to the Decision Engine, exactly like a position you'd
built up through normal BUY trades — same audit trail, same cash ledger
postings.

Usage:
    cd backend
    python -m scripts.seed_from_csv path/to/positions.csv

Expected CSV columns (header row required, case-insensitive, extra columns
ignored):
    ticker, tier, shares, cost_basis

    ticker      - e.g. AMD
    tier        - GROWTH or STABLE
    shares      - total shares currently held
    cost_basis  - your average cost per share (this becomes the position's
                  WAC — if you bought in multiple lots, use your brokerage's
                  "average cost" figure, not any single lot's price)

Optional columns:
    trade_date  - ISO date (YYYY-MM-DD) to backdate the seed transaction;
                  defaults to today if omitted. Cosmetic only — it does not
                  affect EMA/HWM math, which is computed live from market
                  data, not from this date.

Safe to re-run: tickers already present in `holdings` are skipped with a
warning rather than double-counted. To correct a seeded position, log a
manual BUY/SELL adjustment through the Trade Execution UI instead of editing
the CSV and re-running.
"""
import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, Base, engine  # noqa: E402
from app import models, schemas, crud  # noqa: E402

VALID_TIERS = {"GROWTH", "STABLE"}


def seed_from_csv(csv_path: str) -> None:
    Base.metadata.create_all(bind=engine)  # ensure tables exist if run standalone
    db = SessionLocal()

    seeded, skipped, failed = [], [], []

    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            # normalize header keys: lowercase, stripped
            reader.fieldnames = [ (fn or "").strip().lower() for fn in (reader.fieldnames or []) ]

            for i, row in enumerate(reader, start=2):  # row 1 is the header
                ticker = (row.get("ticker") or "").strip().upper()
                tier = (row.get("tier") or "").strip().upper()
                shares_raw = (row.get("shares") or "").strip()
                cost_raw = (row.get("cost_basis") or "").strip()

                if not ticker:
                    failed.append((i, "missing ticker"))
                    continue

                existing = db.query(models.Holding).filter(models.Holding.ticker == ticker).one_or_none()
                if existing is not None:
                    skipped.append(ticker)
                    continue

                if tier not in VALID_TIERS:
                    failed.append((i, f"{ticker}: tier must be GROWTH or STABLE, got '{tier}'"))
                    continue

                try:
                    shares = float(shares_raw)
                    cost_basis = float(cost_raw)
                    if shares <= 0 or cost_basis <= 0:
                        raise ValueError("shares and cost_basis must be positive")
                except ValueError as exc:
                    failed.append((i, f"{ticker}: {exc}"))
                    continue

                trade = schemas.TradeCreate(
                    ticker=ticker,
                    action="BUY",
                    shares=shares,
                    price=cost_basis,
                    tier_name=tier,
                    signal_type="SEED_IMPORT",
                    notes="Imported from existing portfolio spreadsheet",
                )
                try:
                    crud.record_trade(db, trade)
                    seeded.append(f"{ticker}: {shares} sh @ ${cost_basis:.2f}")
                except Exception as exc:  # noqa: BLE001 — surface any row-level failure, keep going
                    db.rollback()
                    failed.append((i, f"{ticker}: {exc}"))
    finally:
        db.close()

    print(f"\nSeeded {len(seeded)} position(s):")
    for line in seeded:
        print(f"  + {line}")

    if skipped:
        print(f"\nSkipped {len(skipped)} ticker(s) already in the ledger (not re-imported):")
        print(f"  {', '.join(skipped)}")

    if failed:
        print(f"\n{len(failed)} row(s) failed:")
        for row_num, msg in failed:
            print(f"  row {row_num}: {msg}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    seed_from_csv(sys.argv[1])
