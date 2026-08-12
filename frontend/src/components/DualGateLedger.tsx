import type { SignalOut } from "../lib/types";

interface Props {
  signals: SignalOut[];
}

function formatPct(value: number): string {
  const pct = (value * 100).toFixed(1);
  return `${value >= 0 ? "+" : ""}${pct}%`;
}

export default function DualGateLedger({ signals }: Props) {
  const rows = [...signals].sort((a, b) => a.ticker.localeCompare(b.ticker));

  return (
    <section className="ledger">
      <h2 className="panel-title">DUAL-GATE LEDGER</h2>

      <div className="ledger-tiles">
        {rows.map((s) => (
          <details key={s.ticker} className="ledger-tile">
            <summary className="ledger-tile-summary">
              <span className="ledger-tile-ticker">{s.ticker}</span>
              <span className="ledger-tile-price">
                ${s.live_price.toFixed(2)}
                {s.is_after_hours ? <span className="ah-badge">AH</span> : null}
              </span>
              <span className={`signal-badge signal-badge-${s.signal.toLowerCase()}`}>
                {s.label}
              </span>
              <span className={`ledger-tile-metric ${s.roi_pct >= 0 ? "accent-green" : "accent-red"}`}>
                ROI {formatPct(s.roi_pct)}
              </span>
            </summary>
            <div className="ledger-tile-detail">
              <div className="ledger-tile-detail-row">
                <span className="ledger-tile-detail-label">Tier</span>
                <span className="ledger-tile-detail-value">{s.tier}</span>
              </div>
              <div className="ledger-tile-detail-row">
                <span className="ledger-tile-detail-label">
                  {s.anchor_type === "HIGH_WATER_MARK" ? "Peak (6mo)" : "WAC"}
                </span>
                <span className="ledger-tile-detail-value">${s.anchor_price.toFixed(2)}</span>
              </div>
              <div className="ledger-tile-detail-row">
                <span className="ledger-tile-detail-label">8/21 EMA</span>
                <span
                  className={`ledger-tile-detail-value ${s.trend === "UP" ? "accent-green" : "accent-red"}`}
                >
                  {s.trend === "UP" ? "▲ UP" : "▼ DN"} ({s.ema8.toFixed(2)} / {s.ema21.toFixed(2)})
                </span>
              </div>
              <div className="ledger-tile-detail-row">
                <span className="ledger-tile-detail-label">Extended trend</span>
                <span className="ledger-tile-detail-value">
                  {s.recent_move_pct !== null ? (
                    <>
                      <span className={s.recent_move_pct >= 0 ? "accent-green" : "accent-red"}>
                        {formatPct(s.recent_move_pct)} (10d)
                      </span>
                      <span className="cell-sub">
                        {s.cross
                          ? `${s.cross === "GOLDEN" ? "Golden" : "Death"} cross${
                              s.pct_vs_200d !== null ? `, ${formatPct(s.pct_vs_200d)} vs 200d` : ""
                            }`
                          : "< 200d history"}
                      </span>
                    </>
                  ) : (
                    "—"
                  )}
                </span>
              </div>
              <div className="ledger-tile-detail-row">
                <span className="ledger-tile-detail-label">Sector</span>
                <span className="ledger-tile-detail-value">
                  {s.sector_label ? `${s.sector_label} (#${s.sector_rank} of 11)` : "—"}
                </span>
              </div>
            </div>
          </details>
        ))}
        {rows.length === 0 ? <p className="empty-state">No active holdings yet — log a trade below to get started.</p> : null}
      </div>

      <div className="ledger-table-wrap has-tile-view">
        <table className="ledger-table">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Tier</th>
              <th>Live Price</th>
              <th>Cost / Peak</th>
              <th>ROI</th>
              <th>8/21 EMA Trend</th>
              <th>Extended Trend</th>
              <th>Sector</th>
              <th>Signal</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.ticker}>
                <td className="cell-ticker" data-label="Ticker">{s.ticker}</td>
                <td data-label="Tier">{s.tier}</td>
                <td data-label="Live Price">
                  ${s.live_price.toFixed(2)}
                  {s.is_after_hours ? <span className="ah-badge">AH</span> : null}
                </td>
                <td data-label="Cost / Peak">
                  ${s.anchor_price.toFixed(2)}
                  <span className="cell-sub">
                    {s.anchor_type === "HIGH_WATER_MARK" ? "peak (6mo)" : "WAC"}
                  </span>
                </td>
                <td data-label="ROI" className={s.roi_pct >= 0 ? "accent-green" : "accent-red"}>
                  {formatPct(s.roi_pct)}
                </td>
                <td data-label="8/21 EMA Trend" className={s.trend === "UP" ? "accent-green" : "accent-red"}>
                  {s.trend === "UP" ? "▲ UP" : "▼ DN"}
                  <span className="cell-sub">
                    {s.ema8.toFixed(2)} / {s.ema21.toFixed(2)}
                  </span>
                </td>
                <td data-label="Extended Trend">
                  {s.recent_move_pct !== null ? (
                    <>
                      <span className={s.recent_move_pct >= 0 ? "accent-green" : "accent-red"}>
                        {formatPct(s.recent_move_pct)} (10d)
                      </span>
                      <span className="cell-sub">
                        {s.cross ? (
                          <>
                            {s.cross === "GOLDEN" ? "Golden cross" : "Death cross"}
                            {s.pct_vs_200d !== null ? `, ${formatPct(s.pct_vs_200d)} vs 200d` : ""}
                          </>
                        ) : (
                          "< 200d history"
                        )}
                      </span>
                    </>
                  ) : (
                    <span className="cell-sub">—</span>
                  )}
                </td>
                <td data-label="Sector">
                  {s.sector_label ? (
                    <>
                      {s.sector_label}
                      <span className="cell-sub">#{s.sector_rank} of 11</span>
                    </>
                  ) : (
                    <span className="cell-sub">—</span>
                  )}
                </td>
                <td data-label="Signal">
                  <span className={`signal-badge signal-badge-${s.signal.toLowerCase()}`}>
                    {s.label}
                  </span>
                </td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={9} className="empty-state">
                  No active holdings yet — log a trade below to get started.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
