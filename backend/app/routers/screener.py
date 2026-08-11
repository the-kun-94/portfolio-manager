"""
Prospect Screener — evaluates a ticker you don't hold yet through the same
Dual-Gate mechanics as the Decision Engine, so a candidate can be checked
before buying instead of only after. See decision_engine.screen_prospect
for why this is a narrower function than evaluate_holding (no WAC, so only
BUY_DIP / WAIT are possible outcomes).
"""
from fastapi import APIRouter, HTTPException

from app import schemas
from app.config import TIER_CONFIG
from app.engine.data_fetcher import get_close_series
from app.engine.decision_engine import screen_prospect

router = APIRouter(prefix="/api", tags=["screener"])


@router.get("/screen/{ticker}", response_model=list[schemas.ProspectSignalOut])
def screen(ticker: str):
    """Evaluates `ticker` against both tiers' discount/momentum rules."""
    ticker = ticker.upper()
    try:
        close_series = get_close_series(ticker)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not fetch price data for '{ticker}': {exc}")

    return [screen_prospect(ticker, tier_name, close_series) for tier_name in TIER_CONFIG]
