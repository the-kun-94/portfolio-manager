"""
Trade execution + cash ledger bookkeeping. Kept separate from the routers
so the recalculation logic (WAC, realized P&L, running cash balance) has
one home and one set of unit tests, regardless of which endpoint calls it.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas


class InsufficientSharesError(Exception):
    pass


class UnknownTickerError(Exception):
    pass


def get_cash_balance(db: Session) -> float:
    total = db.query(func.sum(models.CashLedgerEntry.amount)).scalar()
    return float(total or 0.0)


def _write_cash_entry(
    db: Session,
    entry_type: str,
    amount: float,
    related_ticker: str,
    transaction_id: int,
    notes: str = "",
) -> models.CashLedgerEntry:
    new_balance = get_cash_balance(db) + amount
    entry = models.CashLedgerEntry(
        entry_type=entry_type,
        amount=amount,
        balance_after=new_balance,
        related_ticker=related_ticker,
        transaction_id=transaction_id,
        notes=notes,
    )
    db.add(entry)
    return entry


def record_trade(db: Session, trade: schemas.TradeCreate) -> models.Transaction:
    """
    Logs the trade, recalculates the position's Weighted Average Cost (or
    realized P&L on a sell), and posts the corresponding cash-ledger entry —
    all in one committed transaction so the ledger can never drift out of
    sync with the holdings table.
    """
    holding = db.query(models.Holding).filter(models.Holding.ticker == trade.ticker).one_or_none()

    if holding is None:
        if trade.action == "SELL":
            raise UnknownTickerError(f"Cannot SELL '{trade.ticker}': no existing position.")
        if not trade.tier_name:
            raise UnknownTickerError(
                f"'{trade.ticker}' is a new position — tier_name (GROWTH/STABLE) is required."
            )
        holding = models.Holding(
            ticker=trade.ticker,
            tier_name=trade.tier_name,
            shares=0,
            wac=0,
            realized_pnl=0,
            is_scout=trade.shares * trade.price < 500,  # small starter position heuristic
        )
        db.add(holding)

    txn = models.Transaction(
        ticker=trade.ticker,
        action=trade.action,
        shares=trade.shares,
        price=trade.price,
        signal_type=trade.signal_type,
        notes=trade.notes,
    )
    db.add(txn)
    db.flush()  # populate txn.id for the cash ledger FK

    if trade.action == "BUY":
        new_total_shares = float(holding.shares) + trade.shares
        new_wac = (
            (float(holding.shares) * float(holding.wac)) + (trade.shares * trade.price)
        ) / new_total_shares
        holding.shares = new_total_shares
        holding.wac = new_wac
        holding.is_active = True
        _write_cash_entry(
            db, "BUY_DEBIT", -(trade.shares * trade.price), trade.ticker, txn.id,
            notes=f"BUY {trade.shares} {trade.ticker} @ {trade.price}",
        )

    else:  # SELL
        if trade.shares > float(holding.shares) + 1e-9:
            raise InsufficientSharesError(
                f"Cannot sell {trade.shares} shares of {trade.ticker}; only "
                f"{holding.shares} held."
            )
        realized_delta = (trade.price - float(holding.wac)) * trade.shares
        holding.shares = float(holding.shares) - trade.shares
        holding.realized_pnl = float(holding.realized_pnl) + realized_delta
        if holding.shares <= 1e-9:
            holding.shares = 0
            holding.wac = 0
            holding.is_active = False
        _write_cash_entry(
            db, "SALE_PROCEEDS", trade.shares * trade.price, trade.ticker, txn.id,
            notes=f"SELL {trade.shares} {trade.ticker} @ {trade.price}",
        )

    db.commit()
    db.refresh(txn)
    return txn
