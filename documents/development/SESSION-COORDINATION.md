---
status: active
scope: multi-agent-coordination
last_verified: 2026-10-16
source_sha: d1962f79e1c7337c372de1aebfaaec87dfc7d1c8
---

# Session Coordination — 多 Agent 最小规则

> **只有稳定规则，不存实时 Session 记录。** 正式使用 OpenSpec 后，Change/Design/Tasks 表示开发进度，GitHub Branch/PR/Run 表示版本与验收。无需每次结束都创建新 `AGENT-HANDOFF.md`。

## 并行与所有权

- **可并行**：独立模块文档、独立源码、纯静态/单元测试、低负载明确只读查询。各 Session 独立 Branch/PR，变更前看 Main 和其他开放 PR。
- **需协调代码冲突**：改同一 DAG、Spark/Writer 库、镜像、Terraform root、共用 Config/Workflow、Helm/RBAC，即便 Git 没冲突也可能发生语义冲突。PR/Issue owner 只是信息，不是原子锁。
- **需明确授权 + 人工串行**：共享 Spark Operator/worker02、Airflow Scheduler/真实 DagRun、K8s 节点/存储、S3/PG Writer、Azure Apply，及其它有持久副作用的任务。**不同 Namespace / 不同 Workflow / 同一 Runner Set 不代表互斥**。
- 目前没有一个**已证实覆盖所有 Session、GitHub 仓库和直接 CLI 的分布式资源锁**。以后确需加 Runner concurrency 时须独立审查受影响 Workflow；不在本次文档 PR 实施。

## 运行资源前固定 Gate

1. 报出**确切资源、动作、Workflow、Namespace、目标 SHA、可能副作用**；确认其他 Session 是否占用或即将占用共享资源。
2. 获取用户对**本次动作**的明确协调/执行批准；未确认、占用中或状态不明 → **HOLD**。
3. 获批后仍要只读检查活跃 GitHub Actions、DagRun、SparkApplication/Pod 等实际状态；**授权与资源检查两者缺一不可**。
4. 只运行已批准范围；完成或失败时报告 Run/PR、仍存在的资源和是否安全释放。不要强制清理其他 Session 的 Pods，也不要自动重试未知 PG COMMIT。

## Session 接力（不需要新 Handoff 文件）

新 Agent 读取：`AGENTS.md` → [项目状态](../status/PROJECT-STATUS.md) → 相关组件 →（采用 OpenSpec 后）相关 Change/Tasks → 当前 PR/Main SHA → 相关 Run/独立读回 → **实际共享资源状态**。

采用 OpenSpec 前，暂在 PR 描述/Issue 记录 **Done / Not Done / SHA / Run / Blocker / Next**；之后依赖 Change Tasks/PR/Actions 承接。单个 Session 的时间、窗口、Agent 名称不写入这份长期规则。无人持有的活跃 Job 也不能因「Session 离线」被自动接管。

[原 Portal 协调政策](../../docs/platform-portal/SESSION-COORDINATION-POLICY.zh-CN.md) 的人工共享资源 Gate 在技术上仍适用；其中「TASK004 尚未完成 / A4 Live 尚未执行」等历史 CURRENT 已失效，以新状态为准。
