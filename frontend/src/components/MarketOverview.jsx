import { useEffect, useState } from "react";
import { getCSI300Snapshot } from "../data/market";

export default function MarketOverview() {
  const [market, setMarket] = useState(null);

  useEffect(() => {
    getCSI300Snapshot().then(setMarket).catch(() => setMarket(null));
  }, []);

  if (!market) {
    return <section className="card">正在加载市场数据...</section>;
  }

  return (
    <section className="card">
      <h2>沪深300市场概览</h2>
      <p>数据日期：{market.date || "待更新"}</p>
      <p>样本数量：{market.stocks.length}</p>
      <p>覆盖信息：{JSON.stringify(market.coverage)}</p>
    </section>
  );
}
