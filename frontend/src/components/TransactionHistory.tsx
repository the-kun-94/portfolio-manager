import type { TransactionOut } from "../lib/types";

interface Props {
  trades: TransactionOut[];
}

export default function TransactionHistory({ trades }: Props) {
  return (
    <section className="transaction-history">
      <h2 className="panel-title">TRANSACTION HISTORY</h2>
      <ul className="history-list">
        {trades.map((t) => (
          <li key={t.id} className={`history-item history-${t.action.toLowerCase()}`}>
            <span className="history-action">{t.action}</span>
            <span className="history-ticker">{t.ticker}</span>
            <span className="history-detail">
              {t.shares} sh @ ${t.price.toFixed(2)}
            </span>
            <span className="history-date">{new Date(t.trade_date).toLocaleString()}</span>
          </li>
        ))}
        {trades.length === 0 ? <li className="empty-state">No trades logged yet.</li> : null}
      </ul>
    </section>
  );
}
