# W02 V1.4.1 GitHub Actions 自动化启动包

用途：将 W02 的现有 Pipeline 接到 GitHub Actions。

包含：
- `.github/workflows/w02-weekly-yahoo.yml`：每周抓取 A 股最近交易日数据，并运行 W02 pipeline。
- `.github/workflows/w02-historical-github.yml`：抓取 2021-01-18~2021-01-29 的公开历史归档，用于 V1.4 历史扩展验证。
- `scripts/automation/common.py`：读取 W02 当前 CSI300 成分并做 ticker/exchange 映射。
- `scripts/automation/fetch_yfinance_cn.py`：通过 yfinance/Yahoo Finance 批量获取 A 股日线。
- `scripts/automation/fetch_github_archive.py`：从 GitHub 公开历史归档按股票文件抓取指定日期区间。
- `requirements-automation.txt`
- `config/providers.yaml`

重要：
1. 当前 W02 V1.3 主仓库尚未存在于已连接的 GitHub 账号中，因此本包没有修改旧 `csi300-dashboard`。
2. 建议新建 `w02-global-market-db` 私有仓库后，把本包内容上传进去。
3. Yahoo/GitHub 公开数据的许可状态继续保持 `REVIEW`，默认 `INTERNAL_SNAPSHOT_ONLY`。
4. 工作流只会在 W02 自己的 `run_pipeline.py` 和现有数据结构基础上继续运行，不会用 fixture 提升真实覆盖率。
