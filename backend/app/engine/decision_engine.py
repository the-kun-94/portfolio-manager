"""
The Decision Engine — the mechanical brain of The Kun Algorithm.

Pure function core (`evaluate_holding`) takes a position + its price history
and returns exactly one Signal. No I/O, no side effects, no randomness —
feed it the same inputs twice and it returns the same answer twice. That
determinism is the entire point: it's what "remove human emotion" means in
code.

Order of evaluation matters. Capital protection outranks everything else:
    1. EXIT / Stop Loss      (standard position breached, trend DN)  -> sell 100%
    2. EXIT / Trailing Stop  (legacy winner peak-drop, trend DN)     -> sell 50%
    3. HARVEST               (target hit, trend DN)                  -> sell 25%
    4. RUN WINNER            (target hit or already legacy, trend UP) -> hold
    5. BUY DIP / PULLBACK    (discount hit, trend UP)                -> buy
    6. WAIT                  (nothing actionable, or a falling knife)
"""
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.config import (
    TIER_CONFIG,
    LEGACY_WINNER_ROI_THRESHOLD,
    HIGH_WATER_MARK_LOOKBACK_DAYS,
    TRAILING_STOP_TRIGGER_PCT,
    HARVEST_SELL_FRACTION,
    EXIT_TRAILING_SELL_FRACTION,
    EXIT_STOP_LOSS_SELL_FRACTION,
)
from app.engine.indicators import compute_momentum, high_water_mark


SIGNAL_META = {
    "BUY_DIP": ("🟢", "BUY DIP / PULLBACK"),
    "RUN_WINNER": ("🔥", "RUN WINNER"),
    "HARVEST": ("💰", "HARVEST (Sell 25%)"),
    "EXIT_TRAILING_STOP": ("💰", "EXIT / Trailing Stop (Sell 50%)"),
    "EXIT_STOP_LOSS": ("🛑", "EXIT / Stop Loss (Sell 100%)"),
    "WAIT": ("⚪", "WAIT"),
}


@dataclass
class Signal:
    ticker: str
    tier: str
    live_price: float
    shares: float
    wac: float
    high_water_mark: Optional[float]
    roi_pct: float
    is_legacy_winner: bool
    anchor_type: str          # 'WAC' | 'HIGH_WATER_MARK'
    anchor_price: float
    pct_from_anchor: float
    ema8: float
    ema21: float
    trend: str                 # 'UP' | 'DN'
    signal: str                 # key into SIGNAL_META
    suggested_sell_pct: Optional[float]
    label: str
    reason: str
    is_after_hours: bool = False   # overwritten by the router with a live quote; see routers/signals.py

    # Extended Trend — populated by the router; see engine/extended_trend.py.
    sma50: Optional[float] = None
    sma200: Optional[float] = None
    pct_vs_50d: Optional[float] = None
    pct_vs_200d: Optional[float] = None
    cross: Optional[str] = None
    recent_move_pct: Optional[float] = None


def evaluate_holding(
    ticker: str,
    tier_name: str,
    shares: float,
    wac: float,
    close_prices: pd.Series,
) -> Signal:
    """
    Runs one position through the full Dual-Gate + Hybrid Anchoring pipeline.

    `close_prices` must be a date-sorted Series of daily closes with enough
    history to cover both the 21-EMA warmup and the 6-month HWM lookback
    (a 1y pull, as used by data_fetcher.get_close_series, comfortably covers
    both).
    """
    if tier_name not in TIER_CONFIG:
        raise ValueError(f"Unknown tier '{tier_name}' — must be one of {list(TIER_CONFIG)}")
    tier = TIER_CONFIG[tier_name]

    live_price = float(close_prices.iloc[-1])

    # --- Gate 2: Momentum -------------------------------------------------
    momentum = compute_momentum(close_prices)

    # --- Hybrid Anchoring ---------------------------------------------------
    roi_pct = (live_price - wac) / wac if wac > 0 else 0.0
    is_legacy_winner = roi_pct >= LEGACY_WINNER_ROI_THRESHOLD

    peak_price, _peak_date = high_water_mark(close_prices, HIGH_WATER_MARK_LOOKBACK_DAYS)

    if is_legacy_winner:
        anchor_type = "HIGH_WATER_MARK"
        anchor_price = peak_price
    else:
        anchor_type = "WAC"
        anchor_price = wac

    pct_from_anchor = (live_price - anchor_price) / anchor_price if anchor_price > 0 else 0.0

    # --- Gate 1: Price Anchor thresholds -------------------------------------
    buy_gate1 = pct_from_anchor <= tier.buy_trigger_pct
    harvest_gate1 = pct_from_anchor >= tier.harvest_target_pct

    # Stop loss is ALWAYS measured from true cost basis (WAC), never the
    # high-water mark — that's what "ignoring cost basis for exit decisions"
    # on legacy winners means: the *stop loss* rule stands down for them,
    # replaced by the trailing-stop rule below.
    stop_loss_gate1 = (not is_legacy_winner) and wac > 0 and ((live_price - wac) / wac) <= tier.stop_loss_pct

    # Trailing stop only evaluated for legacy winners, measured off the peak.
    trailing_drop_pct = (live_price - peak_price) / peak_price if peak_price > 0 else 0.0
    trailing_stop_gate1 = is_legacy_winner and trailing_drop_pct <= TRAILING_STOP_TRIGGER_PCT

    trend_up = momentum.trend == "UP"
    trend_dn = momentum.trend == "DN"

    # --- Combine gates into exactly one signal, most severe first -----------
    signal_key: str
    suggested_sell_pct: Optional[float] = None
    reason: str

    # NOTE on gate ordering: harvest_gate1 is only meaningful for STANDARD
    # positions, whose anchor is WAC — a live price can legitimately sit far
    # above cost basis. For LEGACY WINNERS the anchor is the high-water mark,
    # and by construction peak_price = max(..., live_price), so pct_from_anchor
    # can never be positive there. That's not a bug to route around; it's why
    # legacy winners don't re-check "harvest_gate1" at all below — once a
    # position is a legacy winner it has, by definition, already cleared its
    # harvest target, so an UP trend alone (with no trailing-stop breach)
    # means RUN WINNER. Same reasoning applies to buy_gate1: dip-buying off
    # cost basis stops being the relevant question once a position has
    # graduated to legacy-winner status.
    if (not is_legacy_winner) and stop_loss_gate1 and trend_dn:
        signal_key = "EXIT_STOP_LOSS"
        suggested_sell_pct = EXIT_STOP_LOSS_SELL_FRACTION
        reason = (
            f"Standard position breached {tier_name} stop loss "
            f"({tier.stop_loss_pct:.0%} from WAC ${wac:.2f}) and momentum is DN — full exit."
        )
    elif is_legacy_winner and trailing_stop_gate1 and trend_dn:
        signal_key = "EXIT_TRAILING_STOP"
        suggested_sell_pct = EXIT_TRAILING_SELL_FRACTION
        reason = (
            f"Legacy Winner (ROI {roi_pct:.0%}) is down {trailing_drop_pct:.1%} from its "
            f"{HIGH_WATER_MARK_LOOKBACK_DAYS // 30}mo peak (${peak_price:.2f}) and momentum "
            f"is DN — trim 50% to lock in gains."
        )
    elif (not is_legacy_winner) and harvest_gate1 and trend_dn:
        signal_key = "HARVEST"
        suggested_sell_pct = HARVEST_SELL_FRACTION
        reason = (
            f"Hit {tier_name} harvest target ({tier.harvest_target_pct:+.0%} from "
            f"WAC ${wac:.2f}) but momentum flipped DN — trim 25%."
        )
    elif is_legacy_winner and trend_up:
        signal_key = "RUN_WINNER"
        reason = (
            f"Legacy Winner (ROI {roi_pct:+.0%}) with no trailing-stop breach and momentum "
            f"still UP — hold indefinitely, let it run."
        )
    elif (not is_legacy_winner) and harvest_gate1 and trend_up:
        signal_key = "RUN_WINNER"
        reason = (
            f"Past harvest target ({pct_from_anchor:+.1%} from WAC) and momentum "
            f"is still UP — hold indefinitely, let it run."
        )
    elif (not is_legacy_winner) and buy_gate1 and trend_up:
        signal_key = "BUY_DIP"
        reason = (
            f"Hit {tier_name} discount trigger ({tier.buy_trigger_pct:.0%} from WAC "
            f"${anchor_price:.2f}) with momentum UP — confirmed dip, not a falling knife."
        )
    elif (not is_legacy_winner) and buy_gate1 and trend_dn:
        signal_key = "WAIT"
        reason = (
            f"Price is at the discount trigger but momentum is DN — "
            f"falling knife, rule says never buy into a broken trend."
        )
    else:
        signal_key = "WAIT"
        reason = "No threshold breached — position within normal band."

    emoji, label_text = SIGNAL_META[signal_key]

    return Signal(
        ticker=ticker,
        tier=tier_name,
        live_price=live_price,
        shares=shares,
        wac=wac,
        high_water_mark=peak_price,
        roi_pct=roi_pct,
        is_legacy_winner=is_legacy_winner,
        anchor_type=anchor_type,
        anchor_price=anchor_price,
        pct_from_anchor=pct_from_anchor,
        ema8=momentum.ema_fast,
        ema21=momentum.ema_slow,
        trend=momentum.trend,
        signal=signal_key,
        suggested_sell_pct=suggested_sell_pct,
        label=f"{emoji} {label_text}",
        reason=reason,
    )


@dataclass
class ProspectSignal:
    ticker: str
    tier: str
    live_price: float
    six_month_high: float
    pct_from_high: float
    ema8: float
    ema21: float
    trend: str                 # 'UP' | 'DN'
    signal: str                  # 'BUY_DIP' | 'WAIT'
    label: str
    reason: str


def screen_prospect(ticker: str, tier_name: str, close_prices: pd.Series) -> ProspectSignal:
    """
    Same Dual-Gate mechanics as evaluate_holding, for a ticker you don't hold
    yet. There's no WAC to anchor off, so Gate 1 (price discount) is measured
    from the trailing 6-month high instead of cost basis. Only BUY_DIP / WAIT
    are possible outcomes — HARVEST/EXIT signals are meaningless without an
    actual position and cost basis, so they don't apply here.
    """
    if tier_name not in TIER_CONFIG:
        raise ValueError(f"Unknown tier '{tier_name}' — must be one of {list(TIER_CONFIG)}")
    tier = TIER_CONFIG[tier_name]

    live_price = float(close_prices.iloc[-1])
    momentum = compute_momentum(close_prices)
    peak_price, _peak_date = high_water_mark(close_prices, HIGH_WATER_MARK_LOOKBACK_DAYS)
    pct_from_high = (live_price - peak_price) / peak_price if peak_price > 0 else 0.0

    buy_gate1 = pct_from_high <= tier.buy_trigger_pct
    trend_up = momentum.trend == "UP"
    lookback_months = HIGH_WATER_MARK_LOOKBACK_DAYS // 30

    if buy_gate1 and trend_up:
        signal_key = "BUY_DIP"
        reason = (
            f"{pct_from_high:.0%} off its {lookback_months}mo high (${peak_price:.2f}), past "
            f"the {tier_name} {tier.buy_trigger_pct:.0%} discount trigger, with momentum UP — "
            f"confirmed dip, not a falling knife."
        )
    elif buy_gate1 and not trend_up:
        signal_key = "WAIT"
        reason = (
            f"{pct_from_high:.0%} off its {lookback_months}mo high clears the {tier_name} "
            f"discount trigger, but momentum is DN — falling knife, rule says never buy into "
            f"a broken trend."
        )
    else:
        signal_key = "WAIT"
        reason = (
            f"Only {pct_from_high:.0%} off its {lookback_months}mo high — hasn't reached the "
            f"{tier_name} {tier.buy_trigger_pct:.0%} discount trigger yet."
        )

    emoji, label_text = SIGNAL_META[signal_key]

    return ProspectSignal(
        ticker=ticker,
        tier=tier_name,
        live_price=live_price,
        six_month_high=peak_price,
        pct_from_high=pct_from_high,
        ema8=momentum.ema_fast,
        ema21=momentum.ema_slow,
        trend=momentum.trend,
        signal=signal_key,
        label=f"{emoji} {label_text}",
        reason=reason,
    )
