import { useState, FormEvent } from "react";
import { api, ApiError } from "../lib/api";
import type { TradeCreate, TierName } from "../lib/types";

interface Props {
  onTraded: () => void;
}

const TIERS: TierName[] = ["GROWTH", "STABLE"];

export default function TradeForm({ onTraded }: Props) {
  const [ticker, setTicker] = useState("");
  const [action, setAction] = useState<"BUY" | "SELL">("BUY");
  const [shares, setShares] = useState("");
  const [price, setPrice] = useState("");
  const [tierName, setTierName] = useState<TierName>("GROWTH");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setSubmitting(true);

    const sharesNum = parseFloat(shares);
    const priceNum = parseFloat(price);

    if (!ticker.trim() || Number.isNaN(sharesNum) || sharesNum <= 0 || Number.isNaN(priceNum) || priceNum <= 0) {
      setError("Enter a ticker, a positive share count, and a positive price.");
      setSubmitting(false);
      return;
    }

    const trade: TradeCreate = {
      ticker: ticker.trim().toUpperCase(),
      action,
      shares: sharesNum,
      price: priceNum,
      tier_name: tierName,
      signal_type: "MANUAL",
    };

    try {
      const txn = await api.createTrade(trade);
      setSuccessMsg(`Logged: ${txn.action} ${txn.shares} ${txn.ticker} @ $${txn.price.toFixed(2)}`);
      setTicker("");
      setShares("");
      setPrice("");
      onTraded();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Trade failed — try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="trade-form">
      <h2 className="panel-title">EXECUTE TRADE</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <label>
            Ticker
            <input
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="AMD"
              autoComplete="off"
              required
            />
          </label>
          <label>
            Action
            <select value={action} onChange={(e) => setAction(e.target.value as "BUY" | "SELL")}>
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>
          </label>
        </div>

        <div className="form-row">
          <label>
            Shares
            <input
              type="number"
              step="any"
              min="0"
              value={shares}
              onChange={(e) => setShares(e.target.value)}
              placeholder="10"
              required
            />
          </label>
          <label>
            Price
            <input
              type="number"
              step="any"
              min="0"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              placeholder="140.00"
              required
            />
          </label>
        </div>

        {action === "BUY" ? (
          <div className="form-row">
            <label>
              Tier (only used if this is a new ticker)
              <select value={tierName} onChange={(e) => setTierName(e.target.value as TierName)}>
                {TIERS.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>
          </div>
        ) : null}

        {error ? <p className="form-error">{error}</p> : null}
        {successMsg ? <p className="form-success">{successMsg}</p> : null}

        <button type="submit" className={`submit-btn submit-btn-${action.toLowerCase()}`} disabled={submitting}>
          {submitting ? "EXECUTING…" : `EXECUTE ${action}`}
        </button>
      </form>
    </section>
  );
}
