import type { SectorRankOut } from "../lib/types";

interface Props {
  ranks: SectorRankOut[];
}

function formatPct(value: number): string {
  const pct = (value * 100).toFixed(1);
  return `${value >= 0 ? "+" : ""}${pct}%`;
}

export default function SectorStrengthPanel({ ranks }: Props) {
  return (
    <section className="ledger">
      <h2 className="panel-title">SECTOR RELATIVE STRENGTH</h2>
      <p className="panel-subtitle">
        The 11 SPDR sectors ranked by trailing ~3mo performance vs. SPY. Informational only —
        never gates a Dual-Gate signal.
      </p>
      <div className="ledger-table-wrap">
        <table className="ledger-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Sector</th>
              <th>ETF</th>
              <th>RS vs. SPY</th>
            </tr>
          </thead>
          <tbody>
            {ranks.map((r) => (
              <tr key={r.etf_ticker}>
                <td>#{r.rank}</td>
                <td>{r.sector_label}</td>
                <td className="cell-ticker">{r.etf_ticker}</td>
                <td className={r.relative_strength >= 0 ? "accent-green" : "accent-red"}>
                  {formatPct(r.relative_strength)}
                </td>
              </tr>
            ))}
            {ranks.length === 0 ? (
              <tr>
                <td colSpan={4} className="empty-state">
                  Sector data unavailable right now.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
