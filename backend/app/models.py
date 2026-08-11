"""
SQLAlchemy ORM models — mirrors db/schema.sql exactly. If you change one,
change the other; Base.metadata.create_all() (used only for local SQLite
bootstrap) reads these classes, while Postgres deployments should run
db/schema.sql via a real migration tool (Alembic) instead.
"""
from sqlalchemy import (
    Column, Integer, String, Numeric, Boolean, DateTime, Date,
    ForeignKey, CheckConstraint, func
)
from sqlalchemy.orm import relationship

from app.database import Base


class Tier(Base):
    __tablename__ = "tiers"

    tier_name = Column(String, primary_key=True)          # 'GROWTH' | 'STABLE'
    buy_trigger_pct = Column(Numeric(6, 4), nullable=False)
    harvest_target_pct = Column(Numeric(6, 4), nullable=False)
    stop_loss_pct = Column(Numeric(6, 4), nullable=False)
    description = Column(String)

    holdings = relationship("Holding", back_populates="tier")


class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False, unique=True, index=True)
    tier_name = Column(String, ForeignKey("tiers.tier_name"), nullable=False)
    shares = Column(Numeric(18, 6), nullable=False, default=0)
    wac = Column(Numeric(18, 6), nullable=False, default=0)
    realized_pnl = Column(Numeric(18, 6), nullable=False, default=0)
    high_water_mark = Column(Numeric(18, 6))
    high_water_mark_date = Column(Date)
    is_scout = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    tier = relationship("Tier", back_populates="holdings")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("action IN ('BUY','SELL')", name="ck_transactions_action"),
        CheckConstraint("shares > 0", name="ck_transactions_shares_positive"),
        CheckConstraint("price > 0", name="ck_transactions_price_positive"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)
    shares = Column(Numeric(18, 6), nullable=False)
    price = Column(Numeric(18, 6), nullable=False)
    trade_date = Column(DateTime, server_default=func.now())
    signal_type = Column(String)
    notes = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class CashLedgerEntry(Base):
    __tablename__ = "cash_ledger"
    __table_args__ = (
        CheckConstraint(
            "entry_type IN ('DEPOSIT','WITHDRAWAL','SALE_PROCEEDS','BUY_DEBIT','PARK_ETF','UNPARK_ETF')",
            name="ck_cash_ledger_entry_type",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_type = Column(String, nullable=False)
    amount = Column(Numeric(18, 6), nullable=False)
    balance_after = Column(Numeric(18, 6), nullable=False)
    related_ticker = Column(String)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    notes = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class SignalLog(Base):
    __tablename__ = "signal_log"
    __table_args__ = (
        CheckConstraint(
            "signal_type IN ('BUY_DIP','RUN_WINNER','HARVEST','EXIT_TRAILING_STOP','EXIT_STOP_LOSS','WAIT')",
            name="ck_signal_log_signal_type",
        ),
        CheckConstraint("trend IN ('UP','DN')", name="ck_signal_log_trend"),
        CheckConstraint("anchor_type IN ('WAC','HIGH_WATER_MARK')", name="ck_signal_log_anchor_type"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, nullable=False, index=True)
    signal_type = Column(String, nullable=False)
    price_at_signal = Column(Numeric(18, 6), nullable=False)
    anchor_price = Column(Numeric(18, 6), nullable=False)
    anchor_type = Column(String, nullable=False)
    pct_from_anchor = Column(Numeric(8, 4), nullable=False)
    ema8 = Column(Numeric(18, 6))
    ema21 = Column(Numeric(18, 6))
    trend = Column(String)
    suggested_sell_pct = Column(Numeric(5, 4))
    acted_upon = Column(Boolean, nullable=False, default=False)
    generated_at = Column(DateTime, server_default=func.now())


class SectorStrength(Base):
    __tablename__ = "sector_strength"

    id = Column(Integer, primary_key=True, autoincrement=True)
    etf_ticker = Column(String, nullable=False)
    sector_label = Column(String, nullable=False)
    relative_strength = Column(Numeric(8, 4), nullable=False)
    rank = Column(Integer, nullable=False)
    computed_at = Column(DateTime, server_default=func.now())
