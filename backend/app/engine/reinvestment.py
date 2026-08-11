"""
Reinvestment Engine ("The Siphon") — decides which Foundation ETF idle,
unclaimed cash should rotate into when nothing on the Action Feed wants it.

Pure function core, same split as sector_strength.py: no I/O here, just the
rotation rule. The router computes sector ranks and calls in.
"""
from dataclasses import dataclass

from app.engine.sector_strength import SectorRank


@dataclass(frozen=True)
class ReinvestmentRecommendation:
    etf_ticker: str
    reason: str


def recommend_foundation_etf(
    sector_ranks: list[SectorRank],
    sector_proxy: dict[str, str],
    default_etf: str,
) -> ReinvestmentRecommendation:
    """
    A single-sector Foundation ETF (e.g. SMH for Technology) only wins the
    parking-lot slot when its sector is BOTH the #1-ranked SPDR sector by
    trailing relative strength AND still beating the benchmark outright —
    a top rank alone isn't enough if every sector is red. Otherwise cash
    defaults to the broad-market ETF, since an idle parking lot shouldn't
    be making a concentrated bet with no live signal behind it.
    """
    by_label = {r.sector_label: r for r in sector_ranks}

    for etf_ticker, sector_label in sector_proxy.items():
        rank_info = by_label.get(sector_label)
        if rank_info and rank_info.rank == 1 and rank_info.relative_strength > 0:
            return ReinvestmentRecommendation(
                etf_ticker=etf_ticker,
                reason=(
                    f"{sector_label} is the #1 sector by relative strength "
                    f"({rank_info.relative_strength:+.1%} vs. SPY) — rotating into {etf_ticker}."
                ),
            )

    if sector_ranks:
        reason = (
            "No sector proxy is both #1-ranked and outperforming SPY outright — "
            f"defaulting to broad-market {default_etf}."
        )
    else:
        reason = f"Sector strength data unavailable — defaulting to broad-market {default_etf}."

    return ReinvestmentRecommendation(etf_ticker=default_etf, reason=reason)
