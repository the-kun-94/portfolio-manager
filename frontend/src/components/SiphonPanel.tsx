import { useState } from "react";
import { api, ApiError } from "../lib/api";
import type { HoldingOut, ReinvestmentRecommendationOut } from "../lib/types";

interface Props {
  reinvestment: ReinvestmentRecommendationOut | null;
  holdings: HoldingOut[];
  onActed: () => void;
}

// Mirrors backend/app/config.py FOUNDATION_ETFS — the only tickers the
// Reinvestment Engine is allowed to park cash in or unpark from.
const FOUNDATION_ETFS = ["VOO", "SMH"];

function formatUsd(value: number): string {
  return value.toLocaleString("en-US", { style: "currency", currency: "USD" });
}

export default function SiphonPanel({ reinvestment, holdings, onActed }: Props) {
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const parkedPositions = holdings.filter((h) => FOUNDATION_ETFS.includes(h.ticker) && h.shares > 0);

  async function handlePark() {
    setError(null);
    setSuccessMsg(null);
    setBusy(true);
    try {
      const amountNum = amount.trim() ? parseFloat(amount) : undefined;
      if (amount.trim() && (Number.isNaN(amountNum) || (amountNum as number) <= 0)) {
        setError("Enter a positive amount, or leave blank to park the full cash balance.");
        setBusy(false);
        return;
      }
      const txn = await api.parkCash({ amount: amountNum });
      setSuccessMsg(`Parked: ${txn.shares.toFixed(4)} ${txn.ticker} @ $${txn.price.toFixed(2)}`);
      setAmount("");
      onActed();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Park failed — try again.");
    } finally {
      setBusy(false);
    }
  }

  async function handleUnpark(ticker: string) {
    setError(null);
    setSuccessMsg(null);
    setBusy(true);
    try {
      const txn = await api.unparkCash({ ticker });
      setSuccessMsg(`Unparked: ${txn.shares.toFixed(4)} ${txn.ticker} @ $${txn.price.toFixed(2)}`);
      onActed();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unpark failed — try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="trade-form">
      <h2 className="panel-title">REINVESTMENT ENGINE — THE SIPHON</h2>
      <p className="panel-subtitle">
        Routes idle cash into the strongest Foundation ETF (or a broad-market default) when no
        active BUY_DIP signal already wants it. Nothing here fires automatically — every move is
        an explicit trade you trigger below.
      </p>

      {!reinvestment ? (
        <p className="empty-state">Reinvestment data unavailable right now.</p>
      ) : (
        <>
          <p>
            Cash balance: <strong>{formatUsd(reinvestment.cash_balance)}</strong>
          </p>

          {reinvestment.has_actionable_buy ? (
            <p className="form-error">
              Hold off — {reinvestment.actionable_buy_tickers.join(", ")} has an active BUY_DIP
              signal that should claim this cash before it gets parked.
            </p>
          ) : (
            <p>
              Recommended: <strong className="accent-green">{reinvestment.recommended_etf}</strong>
              <br />
              <span className="cell-sub">{reinvestment.reason}</span>
            </p>
          )}

          {reinvestment.style_tilt_note ? (
            <p className={reinvestment.style_tilt === "VALUE_LEADING" ? "form-error" : "cell-sub"}>
              {reinvestment.style_tilt_note}
            </p>
          ) : null}

          <div className="form-row">
            <label>
              Amount to park (blank = full balance)
              <input
                type="number"
                step="any"
                min="0"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder={reinvestment.cash_balance.toFixed(2)}
              />
            </label>
          </div>

          {error ? <p className="form-error">{error}</p> : null}
          {successMsg ? <p className="form-success">{successMsg}</p> : null}

          <button
            type="button"
            className="submit-btn submit-btn-buy"
            disabled={busy || reinvestment.cash_balance <= 0}
            onClick={handlePark}
          >
            {busy ? "WORKING…" : `PARK CASH → ${reinvestment.recommended_etf}`}
          </button>

          {parkedPositions.length > 0 ? (
            <div className="form-row">
              {parkedPositions.map((h) => (
                <button
                  key={h.ticker}
                  type="button"
                  className="submit-btn submit-btn-sell"
                  disabled={busy}
                  onClick={() => handleUnpark(h.ticker)}
                >
                  UNPARK {h.ticker} ({h.shares.toFixed(4)} sh)
                </button>
              ))}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
