---

> **2026-10-31 Fabric FHIR Source Ownership**：[最终 Native ADR](../../architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)。原生 NB/PL/Environment 在 Workspace 对应的 Git Item 目录；唯一新 Python Wheel 是 `shared-data-engine/`；旧独立 Fabric I/O 包方案作废。
status: active
scope: azure-fabric-source-map
last_verified: 2026-10-18
source_sha: 8ad52828599ae95cda95eda4d888fc601ebfdfdc
---

# Azure / Microsoft Fabric — CODE / 源码总导航

> **系统级 CODE 只负责跨组件源码归属；详细源文件导航放在对应组件 CODE.md。** 功能和架构见 [系统 README](README.md)，真实进度只看 [PROJECT-STATUS](../../engineering/status/PROJECT-STATUS.md)。源码位置存在不代表资源已 Apply 或业务端到端成功。

## 组件源码归属

| 组件 | 源码目录 | 唯一组件源码地图 | 约束 |
| --- | --- | --- | --- |
| Terraform | [`azure-fabric/infra-terraform/`](../../../azure-fabric/infra-terraform/) | [Terraform CODE.md](infra-terraform/CODE.md) · [安全设计和历史 Plan](infra-terraform/ARCHITECTURE.md) | 七个 Root/Module，IAM、远程 State、Fabric Item Bootstrap；未证明 Apply |
| Notebooks | [`nb_fhir_ingest.Notebook/`](../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/) | [Notebooks CODE.md](notebooks/CODE.md) | 真实 Fabric Git Item 已导出；Notebook 业务内容仍为空 |
| Environments | [`env_healthcare.Environment/`](../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/) | [Environments CODE.md](environments/CODE.md) | 真实 Fabric Git Item 已导出；Shared Wheel 未发布 |
| Lakehouse | [`lh_omop_analytics.Lakehouse/`](../../../azure-fabric/workspaces/healthcare-omop/lh_omop_analytics.Lakehouse/) | [Lakehouse native files](../../../azure-fabric/workspaces/healthcare-omop/lh_omop_analytics.Lakehouse/lakehouse.metadata.json) | 真实原生元数据已导出；不表示 Delta/Silver E2E PASS |
| Pipelines | [`pl_fhir_ingest.DataPipeline/`](../../../azure-fabric/workspaces/healthcare-omop/pl_fhir_ingest.DataPipeline/) | [Pipelines CODE.md](pipelines/CODE.md) | 真实 Fabric Git Item 已导出；Pipeline activities 仍为空 |

## 跨组件依赖与源码边界

- [Self-Runner Azure-Infra-TF Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) 正式执行 `fabric-workspace/<workspace_name>/<resource_type>/`，而 [Azure-Infra-Shared-TF](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra-shared.yaml) 独立执行 `shared-infra/storage/`。旧 `components/` 路由已经停用；Storage Plan 真实成功，Workspace Plan 因 Runner 缺 Capacity GUID 在预检阶段阻断。
- Terraform [Notebook 安全 Bootstrap](../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) 和 [Pipeline Fail Activity](../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json) **归 Terraform 管理**；所有 Root/Module、Provider 和 IAM 文件请参阅 [Terraform CODE.md](infra-terraform/CODE.md)，此处不复制整张 Terraform 文件表。
- 本地只读 OMOP Exporter、不可变 Manifest、云端 Delta Loader、独立对账尚待开发；过去空的 `exporter/` 和 `tests/` 占位已删除，未来源码归属须依据真实运行位置另行确定。
- Terraform State、已有 Workspace/Blob/Entra 角色以及 Fabric Item GUID 应单独核验。历史七 Root Plan-only [验收记录](infra-terraform/ARCHITECTURE.md#verified-plan-evidence)不代表云端业务 E2E。

## CODE.md 维护要求

Fabric Notebook/Pipeline 新增、删除、移动或改名源码时，**同一 PR** 修改所属 [Notebooks CODE](notebooks/CODE.md) 或 [Pipelines CODE](pipelines/CODE.md)，使用现有 CODE-map CI 验证。Terraform Root/Module、Provider、权限和主要执行入口改变时同步更新 [Terraform CODE](infra-terraform/CODE.md) 并审查 IAM/State/Import；现有 CI **不保证逐一覆盖每个 .tf 文件**。

Azure/Fabric 的 README/CODE/技术说明都在 `documents/systems/azure-fabric/`；源码区只保留真正的程序、Terraform 配置、模板以及 Fabric Item 生成的机器可读元数据，不维护第二份说明性文档。

## Retired johnzhang-test publisher (2026-10-31)

The old `johnzhang-test` native Notebook/Pipeline Smoke items, `trial_smoke_publisher.py`, offline tests and static workflow were removed from current Git after the final Fabric-native ADR. Prior sources remain in [fixed Git history](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/e4640eb4ce4edd8570ca60c9ad2c1b6152941743/azure-fabric/workspaces/johnzhang-test). Self-Runner PR #350 separately retired the executable test workflows. This **does not mean the previously Terraform-applied test Workspace/Lakehouse has been destroyed**; its state-aware retirement remains pending. Do not re-use these test items for `healthcare-omop`.

## OpenLineage compatibility adapter (offline candidate)

- [Candidate Listener config](../../../azure-fabric/openlineage/compatibility.py) · [Offline tests](../../../azure-fabric/openlineage/tests/test_compatibility.py) · [compatibility/authorization notes](../../../azure-fabric/openlineage/README.md). Scala 2.12 local and Scala 2.13 Fabric artifacts are not interchangeable. This source has no live Fabric test authorization; current Fabric Notebook HOLD remains.
## Immutable OpenLineage Blob Publisher (offline only)

- [Publisher entrypoint](../../../azure-fabric/openlineage/publisher.py) · [Fake Azure and recovery tests](../../../azure-fabric/openlineage/tests/test_publisher.py) · [publisher protocol](../../../azure-fabric/openlineage/PUBLISHER.md). Independently verified immutable event readback before committed Manifest; Azure live operations unapproved.

## P2 未发布 Notebook 业务源码（2026-10-31；只属于开发阶段）

**2026-10-31 更新：**P2 唯一业务逻辑已迁入 Fabric Git Native Notebook [notebook-content.py](../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py)。下列开发文件只作为离线加载/安全检查/测试工具，不能单独发布为第二个 Notebook 或 Wheel。正式发布仍需 Environment Publish 与独立云验收。

| 源码文件 | 职责 |
| --- | --- |
| [fhir_ingest_notebook.py](../../../azure-fabric/notebook-development/fhir_ingest_notebook.py) | 离线兼容导入 Native Notebook；不含第二套业务实现 |
| [native_item_readiness.py](../../../azure-fabric/notebook-development/native_item_readiness.py) | Fabric 原生 `.platform` 类型/名称/非零 ID 检查；导出成功仍 HOLD runtime exit 2 |
| [test_notebook_offline.py](../../../azure-fabric/notebook-development/tests/test_notebook_offline.py) | 真实 PySpark Schema/关联和负向离线测试 |
| [README.md](../../../azure-fabric/notebook-development/README.md) | 未发布 Notebook 实施边界和执行安全说明 |
| [fabric-fhir-notebook-offline.yml](../../../.github/workflows/fabric-fhir-notebook-offline.yml) | GitHub-hosted 离线 Wheel 精确 SHA/PySpark 负向 CI |


## Git-to-Fabric event-driven deployment trigger

- [Healthcare main push workflow](../../../.github/workflows/fabric-git-deploy.yml) — GitHub native Notebook/Pipeline source changes start a guarded trigger (no Azure/Fabric token in this public repo).
- [GitHub Actions dispatcher](../../../.github/quality/scripts/fabric_git_dispatch.py) — GitHub Actions workflow_dispatch to the private Self-Runner, pinned to exact Healthcare main SHA; no retry or cloud mutation.
- [Dispatcher offline tests](../../../.github/quality/tests/test_fabric_git_dispatch.py) — validates repo/main/SHA guards, fixed destination and secret-safe error handling.
- Private Self-Runner continues to own the Fabric OIDC, UpdateFromGit reconciliation, canonicalization analysis and independent deployed-definition readback. This trigger does not grant Environment Publish, Spark or Delta execution.
