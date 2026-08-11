"""
Growth vs. Value style tilt — a leading indicator surfaced alongside the
Reinvestment Engine's sector-RS recommendation, never a trigger on its own.

sector_strength.py answers "which sector has been strongest over the
trailing ~3 months" — a confirming signal. This module answers a faster
version of the same question: which style (growth or value) has led over
the trailing ~1 month. A pick like SMH resting on a solid 63-day sector-RS
number can still be flagged here if the shorter-window growth/value spread
has already started bending the other way.

Pure function core, same split as sector_strength.py: no I/O here, the
router fetches price history and passes it in.
"""
from dataclasses import dataclass

import pandas as pd

from app.engine.sector_strength import period_return


@dataclass(frozen=True)
class StyleTilt:
    spread: float   # growth ETF's period return minus value ETF's, over the window
    label: str       # 'GROWTH_LEADING' | 'VALUE_LEADING' | 'NEUTRAL'


def compute_style_tilt(
    growth_close: pd.Series,
    value_close: pd.Series,
    lookback_days: int,
    neutral_band: float,
) -> StyleTilt:
    spread = period_return(growth_close, lookback_days) - period_return(value_close, lookback_days)

    if spread > neutral_band:
        label = "GROWTH_LEADING"
    elif spread < -neutral_band:
        label = "VALUE_LEADING"
    else:
        label = "NEUTRAL"

    return StyleTilt(spread=spread, label=label)
