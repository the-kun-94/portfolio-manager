import type { SignalOut } from "../lib/types";

interface Props {
  signals: SignalOut[];
}

// Best-effort display names for tickers we know about; falls back to the
// ticker itself so unknown symbols still render cleanly.
const TICKER_NAMES: Record<string, string> = {
  AMD: "AMD",
  NVDA: "NVIDIA",
  TGT: "Target",
  AMAT: "Applied Materials",
  SONY: "Sony",
  SMH: "VanEck Semiconductor ETF",
  VTES: "Vanguard Short-Term Tax-Exempt Bond ETF",
  VOO: "Vanguard S&P 500 ETF",
  XLK: "Technology Select Sector SPDR Fund",
  O: "Realty Income",
  GOOG: "Alphabet",
  ORCL: "Oracle",
  NOW: "ServiceNow",
  TEL: "TE Connectivity",
  LITE: "Lumentum",
  RKLB: "Rocket Lab",
  AAOI: "Applied Optoelectronics",
};

function formatMoney(value: number): string {
  return value.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function PortfolioTable({ signals }: Props) {
  const rows = signals
    .map((s) => ({
      ...s,
      equity: s.live_price * s.shares,
      totalReturn: (s.live_price - s.wac) * s.shares,
    }))
    .sort((a, b) => b.totalReturn - a.totalReturn);

  const totalEquity = rows.reduce((sum, r) => sum + r.equity, 0);

  return (
    <section className="ledger">
      <div className="portfolio-header">
        <h2 className="panel-title">PORTFOLIO</h2>
        <div className="portfolio-total">
          <span className="portfolio-total-label">Stocks &amp; ETFs</span>
          <span className="portfolio-total-value">{formatMoney(totalEquity)}</span>
        </div>
      </div>
      <div className="ledger-tiles">
        {rows.map((r) => (
          <details key={r.ticker} className="ledger-tile">
            <summary className="ledger-tile-summary">
              <span className="ledger-tile-ticker">{r.ticker}</span>
              <span className="ledger-tile-price">
                {formatMoney(r.live_price)}
                {r.is_after_hours ? <span className="ah-badge">AH</span> : null}
              </span>
              <span className={`ledger-tile-metric ${r.totalReturn >= 0 ? "accent-green" : "accent-red"}`}>
                {r.totalReturn >= 0 ? "▲" : "▼"} {formatMoney(Math.abs(r.totalReturn))}
              </span>
              <span className="ledger-tile-metric">{formatMoney(r.equity)}</span>
            </summary>
            <div className="ledger-tile-detail">
              <div className="ledger-tile-detail-row">
                <span className="ledger-tile-detail-label">Name</span>
                <span className="ledger-tile-detail-value">{TICKER_NAMES[r.ticker] ?? r.ticker}</span>
              </div>
              <div className="ledger-tile-detail-row">
                <span className="ledger-tile-detail-label">Shares</span>
                <span className="ledger-tile-detail-value">
                  {r.shares.toLocaleString(undefined, { maximumFractionDigits: 3 })}
                </span>
              </div>
              <div className="ledger-tile-detail-row">
                <span className="ledger-tile-detail-label">Average cost</span>
                <span className="ledger-tile-detail-value">{formatMoney(r.wac)}</span>
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
              <th>Name</th>
              <th>Symbol</th>
              <th>Shares</th>
              <th>Price</th>
              <th>Average cost</th>
              <th>Total return</th>
              <th>Equity</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.ticker}>
                <td data-label="Name">{TICKER_NAMES[r.ticker] ?? r.ticker}</td>
                <td className="cell-ticker" data-label="Symbol">{r.ticker}</td>
                <td data-label="Shares">{r.shares.toLocaleString(undefined, { maximumFractionDigits: 3 })}</td>
                <td data-label="Price">
                  {formatMoney(r.live_price)}
                  {r.is_after_hours ? <span className="ah-badge">AH</span> : null}
                </td>
                <td data-label="Average cost">{formatMoney(r.wac)}</td>
                <td data-label="Total return" className={r.totalReturn >= 0 ? "accent-green" : "accent-red"}>
                  {r.totalReturn >= 0 ? "▲" : "▼"} {formatMoney(Math.abs(r.totalReturn))}
                </td>
                <td data-label="Equity">{formatMoney(r.equity)}</td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="empty-state">
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
