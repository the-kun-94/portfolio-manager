import type { NextPage } from "next";
import Head from "next/head";
import CommandHeader from "../components/CommandHeader";
import ActionFeed from "../components/ActionFeed";
import PortfolioTable from "../components/PortfolioTable";
import DualGateLedger from "../components/DualGateLedger";
import SectorStrengthPanel from "../components/SectorStrengthPanel";
import SiphonPanel from "../components/SiphonPanel";
import TradeForm from "../components/TradeForm";
import TransactionHistory from "../components/TransactionHistory";
import { useDashboardData } from "../lib/useDashboardData";
import { useSessionRole } from "../lib/useSessionRole";

const Home: NextPage = () => {
  const { signals, holdings, cash, trades, sectorRanks, reinvestment, loading, error, lastUpdated, refresh } =
    useDashboardData();
  const role = useSessionRole();
  const readOnly = role === "read";

  return (
    <>
      <Head>
        <title>Emotionless Executioner</title>
        <meta
          name="description"
          content="Strictly mechanical, rule-based algorithmic trading terminal."
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <div className="terminal">
        <CommandHeader
          cash={cash}
          lastUpdated={lastUpdated}
          loading={loading}
          error={error}
          onRefresh={refresh}
          readOnly={readOnly}
        />
        <main className="terminal-main">
          <ActionFeed signals={signals} />
          <PortfolioTable signals={signals} />
          <DualGateLedger signals={signals} />
          <SectorStrengthPanel ranks={sectorRanks} />
          <SiphonPanel reinvestment={reinvestment} holdings={holdings} onActed={refresh} readOnly={readOnly} />
          <div className="terminal-columns">
            <TradeForm onTraded={refresh} readOnly={readOnly} />
            <TransactionHistory trades={trades} />
          </div>
        </main>
      </div>
    </>
  );
};

export default Home;
