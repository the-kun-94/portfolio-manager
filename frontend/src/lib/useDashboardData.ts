import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { SignalOut, HoldingOut, TransactionOut, CashSummary, SectorRankOut } from "./types";

// How often the terminal re-polls the Engine. The backend caches yfinance
// pulls for 60s (see config.QUOTE_CACHE_TTL_SECONDS), so anything shorter
// than that just re-reads the same cached bars.
const REFRESH_INTERVAL_MS = 30_000;

interface DashboardData {
  signals: SignalOut[];
  holdings: HoldingOut[];
  cash: CashSummary | null;
  trades: TransactionOut[];
  sectorRanks: SectorRankOut[];
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  refresh: () => void;
}

export function useDashboardData(): DashboardData {
  const [signals, setSignals] = useState<SignalOut[]>([]);
  const [holdings, setHoldings] = useState<HoldingOut[]>([]);
  const [cash, setCash] = useState<CashSummary | null>(null);
  const [trades, setTrades] = useState<TransactionOut[]>([]);
  const [sectorRanks, setSectorRanks] = useState<SectorRankOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [signalsRes, holdingsRes, cashRes, tradesRes, sectorRes] = await Promise.all([
        api.decisionEngine(false),
        api.holdings(),
        api.cashSummary(),
        api.recentTrades(10),
        api.sectorStrength(),
      ]);
      setSignals(signalsRes);
      setHoldings(holdingsRes);
      setCash(cashRes);
      setTrades(tradesRes);
      setSectorRanks(sectorRes);
      setError(null);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reach the Engine.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [load]);

  return { signals, holdings, cash, trades, sectorRanks, loading, error, lastUpdated, refresh: load };
}
