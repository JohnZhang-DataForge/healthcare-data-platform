# Proposal

## Why

Healthcare 项目的新架构已经明确区分自托管的 Kubernetes/OMOP 本地平台与 Azure/Microsoft Fabric 云端平台。原计划的源码根目录 `data-platform/` 容易被理解成包含整个 Hybrid Healthcare 平台。现在源码尚未迁移，是在不影响运行时的情况下确定长期目录名称的合适节点。

## What Changes

- **正式采用** `local-data-platform/` 作为未来本地平台维护源码的唯一目标根目录。
- 保持仓库名 `healthcare-data-platform`、云端目录 `azure-fabric/`、Portal 目录 `platform-portal/`、文档目录 `documents/` 与治理目录 `openspec/` 不变。
- 同步当前架构决策、V2 目标设计、OpenSpec G0–G7 路线及项目状态中的**未来路径**；历史 Git、运行证据和现存 `documents/systems/data-platform/` 组件文档路径不改。
- 明确未来 G5/G6 的前置门槛：G3 的路径检查器与 legacy relocation 白名单仍按旧候选 `data-platform/**` 实现，必须先独立修复、验证并合并，才能迁移到新根目录。

## Capabilities

### New Capabilities

无。本次只统一尚未实施的源码目录命名，没有可观察业务行为新增。

### Modified Capabilities

无。启用 `skip_specs: true`，不编造 Delta Requirements 或 Current Specs。

## Impact

- **仅文档和 OpenSpec Change**；不新建 `local-data-platform/` 实际业务源码，不搬迁、重命名或删除任何代码。
- 不更新 Airflow GitSync/DAG、Docker/Spark、Self-Runner 执行入口，不运行 K8s、PostgreSQL、S3、Azure 或 Terraform。
- 原 NEW_ONLY Person/Visit、Batch、Manifest、Claim/Fingerprint、Writer 的现有运行行为与历史验收结论保持不变。
- 未来真正物理迁移使用独立 `relocate-local-data-platform` Change（G5 审核、G6 实施），并通过独立验证和必要 Runtime 授权。
