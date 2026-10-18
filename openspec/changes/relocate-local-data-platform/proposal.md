# Proposal

## Why

本地 Kubernetes 数据平台原先的业务源码散布于 Healthcare 仓库根目录。已经批准的命名试点 `adopt-local-data-platform-naming` 只决定了未来统一使用 `local-data-platform/`，不包含实际搬迁。2026-10-18 用户随后批准将源码独立备份到 Healthcare-Specs，并允许在完成运行调试前将目录迁移合并到 Main。实施时直接使用 GitHub PR，**没有事先建立正式的 OpenSpec Change**。

本 Change 为已经实施的结构变动提供**事后追溯管理入口**，并把剩余运行兼容修复与验收纳入可接续的 Tasks；绝不将此前 PR 描述为经过事前 OpenSpec 评审。

## What Changes

- 记录原始源码固定 SHA、Healthcare-Specs 私有独立备份、393 个业务文件的来源与校验结果。
- 追溯 Main 已完成的三次合并：PR #225 业务源码物理搬迁、PR #226 文档源码链接与 CODE Map 对齐、PR #227 全仓质量工具移入 `.github/quality/`。
- 保持 `documents/systems/data-platform/` 作为文档组件导航；明确 `local-data-platform/` 才是本地业务**源码**根目录。
- 将尚未完成的 Python Import、Airflow/DAG GitSync、Docker COPY/构建上下文、Spark、Actions/Runner 及独立 E2E 的验证作为未完成任务，不声称此前已运行通过。
- 标记 PR #225 当时的组件检查失败与运行切换风险，不隐瞒历史 Gate。
- 修正必要的事实状态入口，使新 Agent 不再误判“业务源码尚未搬迁”。

## Capabilities

### New Capabilities

无。本 Change 追踪已有源码**位置重构**及其未完成的兼容/验证，不新增可观察业务能力。

### Modified Capabilities

无已批准的业务语义修改。保留 NEW_ONLY Person/Visit、Batch/Manifest/Claim/Fingerprint、Writer/Fencing、DAG ID 等协议与行为不变量。采用 `skip_specs: true`；运行测试不通过或未来行为需要更改时另建相应 Delta Spec/Change，不提前将目标行为写成 Current Specs。

## Impact

- 已改变（历史事实）：仓库 `apps/`、`airflow/`、`spark/`、`images/` 等本地业务根目录移动到 `local-data-platform/`；根目录 `scripts/quality/`、`tests/quality/` 移至 `.github/quality/`，根级这两个目录已退出 Main。
- 已改变（历史事实）：`documents/` 的有效源码链接更新；仓库级 CODE Map 检查器和相关 CI/测试已适配。
- **尚未证明**：生产/实验集群中运行的 DAG、GitSync、镜像及 Spark/PG/S3 全链路已适配新路径。目录内容 Blob 一致、文档链接 CI PASS 不等于运行 E2E PASS。
- 本轮事后纳管 PR **只改 OpenSpec/事实性状态文档**；不执行构建、K8s、Airflow、Spark、PG、S3、Azure、Terraform，也不回放已经完成的批次。
- OpenSpec Change Gate、PR 强制绑定、分支保护和合并后状态自动同步属于**下一轮独立治理修复**，不在本 Change 中悄悄启用。
