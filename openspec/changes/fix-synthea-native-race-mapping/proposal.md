# Proposal

## Why

在 Local DP 8 个镜像完成 Clean Build/GHCR 发布之后，新随机 Batch `synthea-new-only-gh-39524542198`（64 Person、12,446 Visit）在 Atomic Writer 映射阶段报 `BLOCKED=unknown_demographic`，并未完成整个 E2E。随后**两个真实旧/新 Writer 镜像固定 Digest 的只读 A/B**发现：早晨成功 Batch（16 Person、4,259 Visit）两镜像都通过且映射 SHA 一致；后来失败 Batch 两镜像均复现报错，且 64 个 Person 里恰好 **1 个 `race_code=native`** 不在当前 `RACE` 枚举内，Gender/Ethnicity 均受支持。

因此这是针对**该失败 Batch**已证实的既有 Mapper 值域覆盖缺口，不是当前新 Writer 镜像独有的错误；不把它扩大为所有随机 Batch 失败的原因。虽然镜像已发布成功，**业务链路 Writer COMMIT、独立 PG Readback 与幂等 SKIP 尚未通过**，不能宣布迁移完成。

## What Changes

- 调查 Synthea v3.3.0 `native` 的标准语义，并核实当前 OMOP v5.4 对应且有效的标准 Race Concept ID；目前**不得猜数值或默认映射 0**。
- 按验证结果最小化修订现有 Person Canonical → OMOP Race Mapper，并增加缺失类别的正例、未知值负例和与预提交校验一致的诊断；保留已支持值与 Source Value/Fingerprint/Person-Visit 关系。
- 使用原始失败 Batch 的不可变 Parquet 只读回归，不清数据库、不回放已经成功提交的历史 Batch。
- 合并修复到 Main 后，把受影响镜像构建发布与新 Batch 实际 Writer COMMIT/独立 PG-S3 Readback/SKIP 验收移交原 [迁移 Change Task 4.11.5](../relocate-local-data-platform/tasks.md)。

**Non-goals**：本 Bugfix 不删除过时 Shell/测试或旧 GHCR Package，不重构 Writer Fencing/SQL/DAG，不改变 Fabric/Portal，未调查的随机失败 Batch 不强行归因本错误。

## Capabilities

### New Capabilities

- `synthea-omop-demographic-mapping`：首次将既有但缺乏独立 Spec 的 Synthea 人口值 → OMOP 标准 Concept、未知值拒绝、映射幂等保护纳入可测试合同；这是现有业务行为的缺陷修补，不代表已实施新功能。

### Modified Capabilities

- 无现存 Current Spec 需要本方案 PR 修改；目录/镜像迁移的 OpenSpec 不重复拥有 Mapper 业务修复。

## Impact

涉及 `local-data-platform/airflow/dags/task004_cdm_dynamic_adapters.py`、相关前置校验和回归测试、后续受影响 Writer 镜像。证据：[早晨 PASS A/B #39534932448](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39534932448)、[失败 Batch A/B #39535834807](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39535834807)，原 [随机 E2E 现象记录](../relocate-local-data-platform/evidence/LOCAL-DP-NEW-ONLY-WRITER-INTERMITTENT-BATCH-FAILURE-20261020.md) 不修改。

**本次 PR 仅文档/变更手续，不修改业务代码、镜像、K8s、Airflow、PG/S3 或 GHCR Package。**
