# Project Handover Document

## 项目名称

全球市场数据库（Global Market Database）

Repository:

`gggbang520/w02-global-market-db`

Branch:

`main`

---

# 一、当前项目状态恢复报告 V1

## 当前事实

- 项目已建立全球指数数据库流水线。
- 已存在 Provider、History、Snapshot、Weekly、Performance、Audit 等数据处理层。
- 指数层配置存在于 `data/standardized/index_master.json`。
- 报告层位于 `reports/index/`。

## 当前架构

```text
Provider
   ↓
Historical Data
   ↓
Standardized Layer
   ↓
Snapshot
   ↓
Weekly
   ↓
Performance
   ↓
Quality Audit
```

---

# 二、沪深300指数层缺失根因分析 V2

## 已确认事实

1. CN-CS300 存在于 index_master 配置中。
2. 沪深300配置包含：
   - index_id: CN-CS300
   - symbol: 000300.SS
   - source_id: SRC-YAHOO-INDEX
3. `fetch_global_index_history.py` 支持读取 index_master 并生成指数历史数据。
4. 当前问题不是缺少指数配置，而是指数历史数据不足。

## 根因定位

当前链路：

```text
CN-CS300
   ↓
000300.SS
   ↓
Yahoo Index Provider
   ↓
Index History
```

实际结果：

```text
records = 1
status = PARTIAL
```

因此问题定位为：

> Yahoo Index Fetch 返回的沪深300历史数据不足，导致指数历史层覆盖失败。

---

# 三、沪深300指数链路影响分析 V3

## 已确认事实

CN-CS300 已进入下游 Index 流程：

```text
Index Master
   ↓
Fetch
   ↓
History
   ↓
Current State
   ↓
Snapshot
   ↓
Performance
```

但由于历史记录只有单条：

```text
records_available = 1
quality_status = PARTIAL
```

导致：

- daily_change_pct 缺失
- weekly_change_pct 缺失
- monthly_change_pct 缺失
- 历史性能指标不完整

---

# 四、受影响模块

## 直接影响

- `data/history/.../indices/`
- `reports/index/global_index_current_state.json`
- `reports/index/latest_index_snapshot.json`
- `reports/index/global_index_performance.json`

## 未确认受影响

以下模块当前未发现因该问题导致异常：

- CSI300 成分股历史行情流程
- 其他全球指数历史流程
- 股票 Provider 链路

---

# 五、当前最高优先级任务

## 沪深300指数数据源修复审计

后续工作应优先：

1. 审计 Index Provider 层。
2. 增加可靠的沪深300指数历史来源。
3. 保留 Yahoo 作为 secondary provider。
4. 增加历史覆盖质量门槛，避免单条数据进入完整指标流程。

---

# 六、维护原则

本项目继续遵循：

- 数据真实性优先。
- 所有数据必须具备 source_id、source_origin、quality 状态。
- 修改前必须完成读取和根因分析。
- 审计阶段不直接修改业务逻辑。

---

# 文档状态

Created for project handover after:

- 项目状态恢复报告 V1
- 沪深300指数层缺失根因分析 V2
- 沪深300指数链路影响分析 V3
