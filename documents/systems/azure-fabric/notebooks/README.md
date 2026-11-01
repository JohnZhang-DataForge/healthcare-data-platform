---
status: active
scope: azure-fabric-notebooks-overview
last_verified: 2026-11-01
source_sha: 9e667468e278f68c3b26f7eb46b81e58b87bf119
---

# Fabric Notebooks — Git-first 原生代码、数据质量与运行门禁

真实 P2 Notebook 是 Fabric Workspace **healthcare-omop** 的 **nb_fhir_ingest.Notebook**，Git Native 源码位于 [notebook-content.py](../../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py)。它包含 FHIR R4 Patient/Encounter 的 Manifest/SHA 校验、Shared Engine Canonical 处理、Bronze/Silver Delta staging、隔离区、幂等控制与物理读回审查，当前默认 **HALT**，不可直接进行写入业务运行。

早期的 notebooks/ingestion/.gitkeep 是遗留占位目录，不是实际 Fabric Native Item。历史 Terraform Notebook Bootstrap 仅用于基础设施占位，不属于现行业务权威代码。

## 已完成的源文件部署验收

- Git main 修复提交 **9e667468**（[PR #576](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/576)）仅补全 FabricGitSource 的 13 行规范分隔空行，没有改 P2 业务逻辑。
- 用户通过 Fabric Source control 选择 incoming changes 并更新；[Self-Runner Run #41262254996](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/41262254996) 的真实只读 GetDefinition：FabricGitSource **20,053 B**，ipynb **21,689 B / 3 code cells**，业务函数、参数标记与 HALT 存在，Pipeline 安全参数 PASS。
- 这是**Notebook 定义同步 PASS**，不代表 Environment 自定义 Wheel 已有效 Published、Notebook 已绑定可运行依赖或 Silver 数据 E2E 已完成。

## 必须遵守的开发方式

新增或修改原生 Notebook 之前，先读 [Fabric Native Git Authoring Runbook](FABRIC-GIT-AUTHORING-RUNBOOK.md)。它记录了 Fabric 在紧凑单元格分隔排版下丢失整个业务代码的已复现故障、规范 Cell/Parameters Cell/META 示例、Pipeline logicalId/参数和 Environment 的 Staging/Published 区别。

发布应严格分层：Git 代码/CI → 人工审查 Update from Git → 双格式云端 Definition 读回 → Environment Published Wheel/Notebook Binding → 非写入 Smoke → 经授权的 Delta E2E。禁止将 Git 同步、CI 绿色或 Pipeline success 等同于业务完成。

**源码和导航：** [Notebooks CODE](CODE.md) · [Pipelines](../pipelines/README.md) · [Environments CODE](../environments/CODE.md) · [Azure/Fabric 总源码地图](../CODE.md) · [OpenSpec P2](../../../../openspec/changes/ingest-fhir-to-fabric/design.md)。
