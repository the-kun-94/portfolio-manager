import type { CashSummary } from "../lib/types";

function formatCurrency(value: number): string {
  // Floating-point cash-ledger arithmetic can land on a tiny negative
  // epsilon instead of exactly 0 (e.g. after a park/unpark round-trip) —
  // clamp anything under half a cent so it doesn't render as "-$0".
  const clamped = Math.abs(value) < 0.005 ? 0 : value;
  return clamped.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

interface Props {
  cash: CashSummary | null;
  lastUpdated: Date | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export default function CommandHeader({ cash, lastUpdated, loading, error, onRefresh }: Props) {
  return (
    <header className="command-header">
      <div className="brand">
        <span className="brand-mark">THE KUN ALGORITHM</span>
        <span className={`status-dot ${error ? "status-error" : "status-ok"}`} />
        <span className="status-text">{error ? "ENGINE UNREACHABLE" : "LIVE"}</span>
      </div>

      <div className="liquidity-grid">
        <div className="liquidity-cell">
          <span className="liquidity-label">TOTAL LIQUIDITY</span>
          <span className="liquidity-value">{cash ? formatCurrency(cash.total_liquidity) : "—"}</span>
        </div>
        <div className="liquidity-cell">
          <span className="liquidity-label">ACTIVE EQUITY</span>
          <span className="liquidity-value">{cash ? formatCurrency(cash.active_equity_value) : "—"}</span>
        </div>
        <div className="liquidity-cell">
          <span className="liquidity-label">CASH / PARKING LOT</span>
          <span className="liquidity-value accent-green">
            {cash ? formatCurrency(cash.cash_balance) : "—"}
          </span>
        </div>
      </div>

      <div className="header-actions">
        <span className="last-updated">
          {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : "—"}
        </span>
        <button className="refresh-btn" onClick={onRefresh} disabled={loading}>
          {loading ? "SYNCING…" : "REFRESH"}
        </button>
        <button
          className="refresh-btn"
          onClick={async () => {
            await fetch("/api/logout", { method: "POST" });
            window.location.href = "/login";
          }}
        >
          LOG OUT
        </button>
      </div>

      {error ? <div className="header-error">{error}</div> : null}
    </header>
  );
}
