---
status: active
scope: azure-fabric-pipelines-source-map
last_verified: 2026-10-16
source_sha: ddc111db235f9788a08e1b7a6132730e3857707c
---

# Fabric Data Pipelines — CODE 源码地图

**真实 Native Item 归属：** [`pl_fhir_ingest.DataPipeline/`](../../../../azure-fabric/workspaces/healthcare-omop/pl_fhir_ingest.DataPipeline/)（Fabric Git Integration 自动生成的根级目录）。旧 `pipelines/.gitkeep` 占位已经删除；正式 Pipeline 不在子目录内。

**2026-10-31 真实初始化完成：** Fabric Portal 将 `pl_fhir_ingest` 原生定义同步到 GitHub `fabric/native-bootstrap-20261031`，Commit `a6c3d0d6`；`.platform` logicalId 非零。`pipeline-content.json` 仍为 `activities: []`，不意味着 ETL Orchestration 已部署。


**2026-10-31：**旧 `johnzhang-test` Trial Native Notebook/Pipeline Smoke 及其测试已正式从源码树退休（Self-Runner [PR #350](https://github.com/JohnZhang-DataForge/Self-Runner/pull/350)、Healthcare 清理 PR）。不再维护该测试 Workspace 的原生 Item 文件。历史 Item 定义可查阅 [退役前固定 Git 历史](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/e4640eb4ce4edd8570ca60c9ad2c1b6152941743/azure-fabric/workspaces/johnzhang-test)，不得照旧发布。**曾通过 Terraform Apply 的 Workspace/Lakehouse 尚未确认云端删除，等待独立 State-aware teardown。**

## 实际拥有的 Fabric 原生源码文件

| 原生源码文件 | 功能 |
| --- | --- |
| [pl_fhir_ingest.DataPipeline/.platform](../../../../azure-fabric/workspaces/healthcare-omop/pl_fhir_ingest.DataPipeline/.platform) | Fabric Git 同步的真实 Pipeline Item 元数据；不要手工改 logicalId |
| [pl_fhir_ingest.DataPipeline/pipeline-content.json](../../../../azure-fabric/workspaces/healthcare-omop/pl_fhir_ingest.DataPipeline/pipeline-content.json) | 包含一个引用真实 Notebook 原生 logicalId 的受控 TridentNotebook Activity；G5 只读 Silver Approval 模式参数通过 Pipeline Expression 显式传入；默认 HALT、两项写授权永久 false、无自动重试；云端 Pipeline definition / Run 尚待独立读回 |

**以后如何更新：**新增真实 Data Pipeline Item 时，应将其实际的 `.platform`、`pipeline-content.json` 及其他生成文件以**逐文件相对 Markdown 链接**登记在上表。静态 CODE-map CI 会检查源码完整性和归属；新增、删除或迁移源码时，必须在同一 PR 更新本 `CODE.md`。

Terraform 中的[默认失败保护定义](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json)和[Notebook Activity 模板](../../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-notebook.json)继续由[总 CODE.md](../CODE.md)中的基础设施部分导航；它们不是已运行的 Fabric 原生 Git Item。

**继续阅读：**[Pipelines 职责](README.md) · [Notebooks CODE.md](../notebooks/CODE.md) · [Azure/Fabric 概览](../README.md)。

## G5 Silver read-only Pipeline 参数契约（2026-11-03 候选）

- 单 Notebook Activity，复用 `nb_fhir_ingest` 中已经 G4 真实验收的 `SILVER_READBACK_ONLY`；通过 Expression 传递 run_mode / request_id / manifest_sha256 / source_preservation_strategy / patient_contract_json / encounter_contract_json。
- `run_mode` 默认 `HALT`，`source_preservation_strategy` 默认 `HALT`，所有请求和 Contract 字段默认空；`write_authorized=false`、`retention_preflight_verified=false` 不允许 Pipeline 参数覆盖；`retry=0`，无 schedule。
- 不允许以 Pipeline SUCCESS 代替实际 Notebook exitValue 或 Approval、两张 Delta 的独立物理读回。真正 Candidate/Gold E2E 尚未包含在本静态变更内；Fabric Workspace UpdateFromGit / getDefinition / Pipeline Job Instance / 原始 G4 Replay 需要单独实际验收。
- 本分支 CI 对新版 `healthcare_data_engine` 0.1.2 候选 Wheel SHA 与**仍已发布的** 0.1.1 原生 Environment Wheel SHA 作**两个独立检查**，Native Notebook 回归继续用 0.1.1。任何用 0.1.2 的 Notebook 真运行必须先独立 publish/readback。

## FHIR → Fabric OMOP stage-1 interface (2026-11-03, versioned)

- [FHIR–OMOP Handoff v1 decision, ownership and acceptance](FHIR-OMOP-HANDOFF-V1.md): G5 approved Silver → independent Fabric Warehouse OMOP F1/F2/F3; **contract-only, no writes**.
- [Machine handoff contract](../../../../shared-data-engine/contracts/fabric-fhir-omop-handoff-v1.json), [pure structural-only validator](../../../../shared-data-engine/src/healthcare_data_engine/models/fabric_omop_handoff.py), [negative tests](../../../../shared-data-engine/tests/test_fabric_omop_handoff.py), [OpenSpec](../../../../openspec/changes/fabric-fhir-omop-handoff-v1/design.md).
- Live read-only G5 Pipeline/physical Silver acceptance: [Self-Runner #41636454542](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41636454542). Existing OMOP F0 39/432 empty base schema physical PASS: [#41648858578](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41648858578). OMOP F1 Identity + Vocabulary and Gold Writer remain separate work; **no Gold COMMITTED claim**.
