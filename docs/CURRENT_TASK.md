# CURRENT TASK

## 项目

全球市场数据库 W02

## 当前任务

沪深300 Index Provider Layer V1 实施

## 当前阶段

实施方案确认完成。

状态：

等待代码实施。

## 当前问题

CN-CS300：

index_master配置存在。

symbol:

000300.SS

provider:

SRC-YAHOO-INDEX

问题：

Yahoo Index历史返回不足。

records=1。

## 实施目标

建立：

Index Provider Layer

支持：

- CSI Official Provider
- Yahoo Secondary Provider
- Manual Import Provider

## 修改原则

必须遵守：

1. 先读取真实仓库
2. 输出修改计划
3. 确认后修改
4. 修改后测试
5. 再commit

## 禁止

当前阶段禁止：

- 修改业务代码
- 删除旧数据
- 覆盖SRC-YAHOO-INDEX历史
- 修改股票CSI300链路

## 下一步

进入：

《沪深300 Index Provider Layer V1代码实施》

前：

需要再次确认：

- CSI数据来源
- Provider接口设计
- 修改文件列表
