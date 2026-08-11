"""
The Kun Algorithm — FastAPI entrypoint.

Run locally:
    cd backend
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8000

Deploy (e.g. Render): start command is
    uvicorn app.main:app --host 0.0.0.0 --port $PORT
See DEPLOYMENT.md at the repo root for the full cloud walkthrough.

On startup this creates any missing tables (safe/idempotent — it only
creates tables that don't already exist, so it's fine to run against a
long-lived Postgres instance on every deploy) and seeds the two tiers from
config.TIER_CONFIG if they aren't present yet. This stands in for a real
migration tool (Alembic) for now; swap it in before the schema needs to
evolve without a table wipe.
"""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import verify_api_key
from app.database import engine, SessionLocal, Base
from app import models
from app.config import TIER_CONFIG, CORS_ORIGINS
from app.routers import signals, trades, portfolio, cash, reinvestment

app = FastAPI(
    title="The Kun Algorithm",
    description="Strictly mechanical, rule-based algorithmic trading engine.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_auth = [Depends(verify_api_key)]
app.include_router(signals.router, dependencies=_auth)
app.include_router(trades.router, dependencies=_auth)
app.include_router(portfolio.router, dependencies=_auth)
app.include_router(cash.router, dependencies=_auth)
app.include_router(reinvestment.router, dependencies=_auth)


@app.on_event("startup")
def bootstrap_db() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(models.Tier).count() == 0:
            for tier_name, cfg in TIER_CONFIG.items():
                db.add(models.Tier(
                    tier_name=tier_name,
                    buy_trigger_pct=cfg.buy_trigger_pct,
                    harvest_target_pct=cfg.harvest_target_pct,
                    stop_loss_pct=cfg.stop_loss_pct,
                ))
            db.commit()
    finally:
        db.close()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "system": "The Kun Algorithm"}
