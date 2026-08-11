-- ============================================================================
-- Emotionless Executioner — Database Schema
-- Replaces portfolio.csv with a relational ledger.
-- Written for PostgreSQL; fully compatible with SQLite (dev default) —
-- avoid Postgres-only types in application code paths that must run on both.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. TIERS — static rule configuration per volatility class.
--    Seeded once; edit thresholds here, not in application code.
-- ----------------------------------------------------------------------------
CREATE TABLE tiers (
    tier_name           TEXT PRIMARY KEY,             -- 'GROWTH' | 'STABLE'
    buy_trigger_pct     NUMERIC(6,4) NOT NULL,         -- e.g. -0.10 for -10% from anchor
    harvest_target_pct  NUMERIC(6,4) NOT NULL,         -- e.g.  0.15 for +15% gain
    stop_loss_pct       NUMERIC(6,4) NOT NULL,         -- e.g. -0.15 from cost basis
    description         TEXT
);

INSERT INTO tiers (tier_name, buy_trigger_pct, harvest_target_pct, stop_loss_pct, description) VALUES
    ('GROWTH', -0.10, 0.15, -0.15, 'High-volatility names (AMD, NVDA, ...)'),
    ('STABLE', -0.05, 0.10, -0.08, 'Blue-chip / income names (MSFT, O, TGT, ...)');

-- ----------------------------------------------------------------------------
-- 2. HOLDINGS — current live position state, one row per ticker.
--    This is the "book of record" the Decision Engine reads on every pass.
--    wac / shares are derived from TRANSACTIONS but cached here for speed;
--    a trade insert must recompute and update this row in the same txn.
-- ----------------------------------------------------------------------------
CREATE TABLE holdings (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,  -- SERIAL on Postgres
    ticker                  TEXT NOT NULL UNIQUE,
    tier_name               TEXT NOT NULL REFERENCES tiers(tier_name),
    shares                  NUMERIC(18,6) NOT NULL DEFAULT 0,
    wac                     NUMERIC(18,6) NOT NULL DEFAULT 0,   -- Weighted Average Cost
    realized_pnl            NUMERIC(18,6) NOT NULL DEFAULT 0,
    high_water_mark         NUMERIC(18,6),                       -- peak close, trailing lookback window
    high_water_mark_date    DATE,
    is_scout                BOOLEAN NOT NULL DEFAULT FALSE,      -- small starter/probe position
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,       -- FALSE once fully exited (kept for history)
    created_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_holdings_active ON holdings(is_active);

-- ----------------------------------------------------------------------------
-- 3. TRANSACTIONS — immutable trade log. Source of truth for WAC and P&L.
--    Every BUY/SELL logged via the Trade Execution UI lands here first;
--    holdings.wac/shares are then recalculated from this table.
-- ----------------------------------------------------------------------------
CREATE TABLE transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    action          TEXT NOT NULL CHECK (action IN ('BUY', 'SELL')),
    shares          NUMERIC(18,6) NOT NULL CHECK (shares > 0),
    price           NUMERIC(18,6) NOT NULL CHECK (price > 0),
    trade_date      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    signal_type     TEXT,             -- e.g. 'BUY_DIP', 'HARVEST', 'STOP_LOSS', 'MANUAL'
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_ticker ON transactions(ticker);
CREATE INDEX idx_transactions_date ON transactions(trade_date DESC);

-- ----------------------------------------------------------------------------
-- 4. CASH_LEDGER — the Universal CASH account ("The Siphon").
--    Every SELL credits this; every BUY debits it. Running balance_after
--    lets the frontend Command Header render total liquidity with one query.
-- ----------------------------------------------------------------------------
CREATE TABLE cash_ledger (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_type      TEXT NOT NULL CHECK (
                        entry_type IN ('DEPOSIT', 'WITHDRAWAL', 'SALE_PROCEEDS',
                                        'BUY_DEBIT', 'PARK_ETF', 'UNPARK_ETF')
                    ),
    amount          NUMERIC(18,6) NOT NULL,        -- positive = inflow, negative = outflow
    balance_after   NUMERIC(18,6) NOT NULL,
    related_ticker  TEXT,                          -- ticker that generated/consumed this entry
    transaction_id  INTEGER REFERENCES transactions(id),
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cash_ledger_date ON cash_ledger(created_at DESC);

-- ----------------------------------------------------------------------------
-- 5. SIGNAL_LOG — every signal the Decision Engine has ever emitted.
--    Feeds the Action Feed (latest, unacted signals) and provides an audit
--    trail proving the system is acting mechanically, not emotionally.
-- ----------------------------------------------------------------------------
CREATE TABLE signal_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    signal_type     TEXT NOT NULL CHECK (
                        signal_type IN ('BUY_DIP', 'RUN_WINNER', 'HARVEST',
                                          'EXIT_TRAILING_STOP', 'EXIT_STOP_LOSS', 'WAIT')
                    ),
    price_at_signal NUMERIC(18,6) NOT NULL,
    anchor_price    NUMERIC(18,6) NOT NULL,
    anchor_type     TEXT NOT NULL CHECK (anchor_type IN ('WAC', 'HIGH_WATER_MARK')),
    pct_from_anchor NUMERIC(8,4) NOT NULL,
    ema8            NUMERIC(18,6),
    ema21           NUMERIC(18,6),
    trend           TEXT CHECK (trend IN ('UP', 'DN')),
    suggested_sell_pct NUMERIC(5,4),                 -- 0.25 / 0.50 / 1.00 for exits
    acted_upon      BOOLEAN NOT NULL DEFAULT FALSE,
    generated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signal_log_ticker_date ON signal_log(ticker, generated_at DESC);
CREATE INDEX idx_signal_log_actionable ON signal_log(acted_upon, signal_type);

-- ----------------------------------------------------------------------------
-- 6. SECTOR_STRENGTH — Relative Strength Sector Leaderboard, used by the
--    Reinvestment Engine to decide which Foundation ETF (VOO / SMH / etc.)
--    parked cash rotates into when there is no active BUY signal.
-- ----------------------------------------------------------------------------
CREATE TABLE sector_strength (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    etf_ticker          TEXT NOT NULL,          -- e.g. 'VOO', 'SMH', 'XLK'
    sector_label        TEXT NOT NULL,
    relative_strength    NUMERIC(8,4) NOT NULL,  -- e.g. 63-day RS score vs. SPY
    rank                INTEGER NOT NULL,
    computed_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sector_strength_date ON sector_strength(computed_at DESC);
