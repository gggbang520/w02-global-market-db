const parseGithubJson = async (url) => {
  const response = await fetch(url);
  const json = await response.json();

  if (json.content) {
    return JSON.parse(json.content);
  }

  return json;
};

export async function getCSI300Snapshot() {
  const url = "/w02-global-market-db/data/current/weekly/CSI300__weekly_snapshot.json";
  const data = await parseGithubJson(url);

  return {
    indexId: data.index_id,
    date: data.week_end_trade_date,
    coverage: data.coverage,
    stocks: data.records || []
  };
}

export async function getStockDaily() {
  const url = "/w02-global-market-db/data/current/stocks/price_daily.json";
  const data = await parseGithubJson(url);

  return {
    version: data.data_version,
    stocks: data.records || [],
    coverage: data.coverage || {}
  };
}

export async function getValuation() {
  const url = "/w02-global-market-db/data/current/stocks/valuation_daily.json";
  const data = await parseGithubJson(url);

  return {
    records: data.records || [],
    coverage: data.coverage || 0
  };
}
