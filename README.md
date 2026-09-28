# W02 V0.8｜CSI300 批量行情接入层与多来源 Provider 架构

V0.8 建立统一 MarketDataProvider 抽象、CSV/XLS/XLSX/JSON 批量文件入口、Listing Master 身份映射、OHLC/交易日/重复校验、Coverage、Provider Reconciliation、License Gate、Price Lineage、Import Receipt。

当前运行没有新的市场价格文件进入 `data/raw/inbox/market/`，因此真实覆盖率没有提升。既有 4 条 2026-09-24 Secondary price records 保留为 SECONDARY。

真实状态：AUTO_PROVIDER=0；MANUAL_PROVIDER_FILE=0；OFFICIAL=0；SECONDARY=4；CSI300 price coverage=4/300=1.33%。

运行：`python scripts/ingest_market_data.py <file>` 或 `python scripts/run_pipeline.py`。
