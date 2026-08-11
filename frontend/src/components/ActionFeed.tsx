import type { SignalOut, SignalType } from "../lib/types";

// Only these signals belong on the Action Feed — RUN_WINNER and WAIT are
// informational states, not "go do something right now" alerts.
const ACTIONABLE = new Set<SignalType>([
  "BUY_DIP",
  "HARVEST",
  "EXIT_TRAILING_STOP",
  "EXIT_STOP_LOSS",
]);

// Capital-protection-first, same ordering as the backend's gate evaluation.
const SEVERITY_ORDER: Record<string, number> = {
  EXIT_STOP_LOSS: 0,
  EXIT_TRAILING_STOP: 1,
  HARVEST: 2,
  BUY_DIP: 3,
};

const SIGNAL_CLASS: Record<string, string> = {
  EXIT_STOP_LOSS: "signal-exit-stop",
  EXIT_TRAILING_STOP: "signal-exit-trailing",
  HARVEST: "signal-harvest",
  BUY_DIP: "signal-buy",
};

interface Props {
  signals: SignalOut[];
}

export default function ActionFeed({ signals }: Props) {
  const actionable = signals
    .filter((s) => ACTIONABLE.has(s.signal))
    .sort((a, b) => SEVERITY_ORDER[a.signal] - SEVERITY_ORDER[b.signal]);

  return (
    <section className="action-feed">
      <h2 className="panel-title">ACTION FEED</h2>
      {actionable.length === 0 ? (
        <p className="empty-state">No actionable signals right now. System is watching.</p>
      ) : (
        <ul className="action-list">
          {actionable.map((s) => (
            <li key={s.ticker} className={`action-item ${SIGNAL_CLASS[s.signal] ?? ""}`}>
              <div className="action-item-main">
                <span className="action-ticker">{s.ticker}</span>
                <span className="action-label">{s.label}</span>
              </div>
              <div className="action-item-detail">
                <span>${s.live_price.toFixed(2)}</span>
                <span>{(s.pct_from_anchor * 100).toFixed(1)}% from anchor</span>
                {s.suggested_sell_pct ? (
                  <span>Sell {(s.suggested_sell_pct * 100).toFixed(0)}%</span>
                ) : null}
              </div>
              <p className="action-reason">{s.reason}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
