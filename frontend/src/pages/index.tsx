import type { NextPage } from "next";
import Head from "next/head";
import CommandHeader from "../components/CommandHeader";
import ActionFeed from "../components/ActionFeed";
import PortfolioTable from "../components/PortfolioTable";
import DualGateLedger from "../components/DualGateLedger";
import SectorStrengthPanel from "../components/SectorStrengthPanel";
import TradeForm from "../components/TradeForm";
import TransactionHistory from "../components/TransactionHistory";
import { useDashboardData } from "../lib/useDashboardData";

const Home: NextPage = () => {
  const { signals, cash, trades, sectorRanks, loading, error, lastUpdated, refresh } = useDashboardData();

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
        />
        <main className="terminal-main">
          <ActionFeed signals={signals} />
          <PortfolioTable signals={signals} />
          <DualGateLedger signals={signals} />
          <SectorStrengthPanel ranks={sectorRanks} />
          <div className="terminal-columns">
            <TradeForm onTraded={refresh} />
            <TransactionHistory trades={trades} />
          </div>
        </main>
      </div>
    </>
  );
};

export default Home;
