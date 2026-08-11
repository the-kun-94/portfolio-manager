# Emotionless Executioner

A strictly mechanical, rule-based algorithmic trading platform. No news
feeds, no analyst ratings — just price, momentum, and position math.

## Directory Structure

```
emotionless-executioner/
├── backend/                       # FastAPI "Engine"
│   ├── requirements.txt
│   └── app/
│       ├── main.py                # FastAPI app, CORS, router wiring, dev DB bootstrap
│       ├── config.py               # ALL tunable thresholds live here (tiers, anchoring, sizing)
│       ├── database.py             # SQLAlchemy engine/session (SQLite dev / Postgres prod)
│       ├── models.py               # ORM models mirroring db/schema.sql
│       ├── schemas.py              # Pydantic request/response models
│       ├── crud.py                 # Trade execution: WAC recalculation, cash ledger postings
│       ├── engine/                 # Pure quant logic — no I/O except data_fetcher
│       │   ├── indicators.py       # 8/21 EMA, high-water-mark helpers (Gate 2)
│       │   ├── data_fetcher.py     # yfinance wrapper with a small in-memory cache
│       │   └── decision_engine.py  # THE Decision Engine — Dual-Gate + Hybrid Anchoring
│       └── routers/
│           ├── signals.py          # GET /api/decision-engine  (Action Feed data source)
│           ├── trades.py           # POST /api/trades          (Trade Execution UI)
│           ├── portfolio.py        # GET /api/holdings, /api/cash-summary
│           └── cash.py             # manual deposit/withdraw + ledger read
│   ├── scripts/
│   │   ├── seed_from_csv.py        # one-time import of an existing portfolio spreadsheet
│   │   └── positions_example.csv   # expected column format
│   └── .env.example
├── db/
│   └── schema.sql                  # canonical DDL — replaces portfolio.csv
├── frontend/                       # Next.js "Terminal" — see frontend/README.md
│   └── src/{pages,components,lib,styles}/
├── render.yaml                     # Render Blueprint for the backend
├── DEPLOYMENT.md                   # Neon + Render + Vercel, step by step
└── README.md
```

## Quickstart (backend, local)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

First run against the default SQLite file creates the tables and seeds the
two tiers from `config.TIER_CONFIG`.

Try it:

```bash
# Seed a position (creates the holding since it's a new ticker)
curl -X POST localhost:8000/api/trades -H "Content-Type: application/json" -d '{
  "ticker": "AMD", "action": "BUY", "shares": 10, "price": 140.00, "tier_name": "GROWTH"
}'

# Run the Decision Engine across all holdings
curl localhost:8000/api/decision-engine
```

Already have an existing portfolio to import instead of logging trades one
by one? Fill in `backend/scripts/positions_example.csv` with your real
tickers/tiers/shares/cost-basis and run:

```bash
python -m scripts.seed_from_csv path/to/your_positions.csv
```

## Quickstart (frontend, local)

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000` — needs the backend running for data to appear.

## Going live

`DEPLOYMENT.md` walks through deploying this for real: Neon (free,
non-expiring Postgres) + Render (backend) + Vercel (frontend), all free
tier, verified current as of August 2026.

## Design notes worth knowing before you extend this

- **Gate ordering is capital-protection-first.** `decision_engine.evaluate_holding`
  checks EXIT_STOP_LOSS, then EXIT_TRAILING_STOP, then HARVEST, then RUN_WINNER,
  then BUY_DIP, then WAIT — in that order — because a position can technically
  qualify for more than one signal at once, and only one action should fire.
- **Hybrid Anchoring gates are legacy/standard-exclusive by design, not by
  accident.** Once a position crosses the 50% ROI line, its anchor becomes the
  6-month high-water mark. Since the HWM is `max(price history)`, a legacy
  winner's live price can never sit *above* its own anchor — so `harvest_gate1`
  and `buy_gate1` (both defined as "X% *above/below* anchor") are mathematically
  never true for legacy winners. The engine accounts for this explicitly:
  legacy winners get RUN_WINNER by default whenever trend is UP and the
  trailing-stop hasn't fired, rather than re-testing a gate that can't pass.
  This was caught and fixed via the unit tests in this delivery — worth
  re-reading `decision_engine.py`'s inline comment on this if you modify the
  gate logic.
- **Stop loss vs. trailing stop are mutually exclusive by position type.**
  Stop loss (100% exit) only applies to standard (non-legacy) positions,
  measured off WAC. Trailing stop (50% exit) only applies to legacy winners,
  measured off the high-water mark. This mirrors the brief's instruction that
  "the original cost basis is ignored for exit decisions" once a position
  becomes a legacy winner.
- **`only_actionable=true` on `GET /api/decision-engine`** is what should back
  the frontend Action Feed; the unfiltered response (including WAIT/RUN_WINNER
  rows) is what the Dual-Gate Ledger table needs for its Signal Status column.
- **Sector Relative Strength / Reinvestment Engine** — `db/schema.sql` includes
  a `sector_strength` table and `config.FOUNDATION_ETFS` lists VOO/SMH as the
  parking-lot targets, but the actual RS-ranking computation and auto-rotation
  logic ("The Siphon") is not implemented yet — that's the natural next
  backend milestone.

## What's verified vs. not in this delivery

All Python files pass `py_compile`, and `decision_engine.evaluate_holding` was
exercised against six hand-built and randomized price-history fixtures
covering every signal type (BUY_DIP, EXIT_STOP_LOSS, EXIT_TRAILING_STOP,
RUN_WINNER for both standard and legacy positions, and the "falling knife"
WAIT case) — all passed.

The FastAPI/SQLAlchemy backend layer (`main.py`, routers, `crud.py`,
`seed_from_csv.py`) and the entire Next.js frontend could **not** be
installed or run in the sandbox this was built in — it has no network
access to PyPI or the npm registry, only to a small allowlist. Everything
was written carefully and cross-checked by hand (request/response shapes
matched field-by-field between `schemas.py` and `frontend/src/lib/types.ts`,
CSS class names cross-referenced against every component, etc.), but neither
`uvicorn app.main:app --reload` nor `npm run build` has actually been
executed yet. Treat your first local run (or the Vercel build log, if you
go straight to deploying) as the real first compile check, and send me
whatever error comes up — it'll be fast to fix with the actual traceback in
hand.
