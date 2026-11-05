---
status: active
scope: azure-fabric-source-map
last_verified: 2026-11-04
source_sha: 5a7bd15977b307c358ff50155888a58f813e06ed
---

# Azure / Microsoft Fabric — CODE / 源码总导航

> **2026-10-31 Fabric FHIR Source Ownership**：[最终 Native ADR](../../architecture/design/FABRIC-NATIVE-NOTEBOOK-PIPELINE-ENVIRONMENT-ADR-20261031.md)。根级 Native NB/PL/Environment；唯一新 Shared Wheel；不创建第二个 Fabric I/O 包。目录位置以已合并的 P1 OpenSpec 为准。

> **系统级 CODE 只负责跨组件源码归属；详细源文件导航放在对应组件 CODE.md。** 功能和架构见 [系统 README](README.md)，真实进度只看 [PROJECT-STATUS](../../engineering/status/PROJECT-STATUS.md)。源码位置存在不代表资源已 Apply 或业务端到端成功。

## 组件源码归属

| 组件 | 源码目录 | 唯一组件源码地图 | 约束 |
| --- | --- | --- | --- |
| Terraform | [`azure-fabric/infra-terraform/`](../../../azure-fabric/infra-terraform/) | [Terraform CODE.md](infra-terraform/CODE.md) · [安全设计和历史 Plan](infra-terraform/ARCHITECTURE.md) | 七个 Root/Module，IAM、远程 State、Fabric Item Bootstrap；未证明 Apply |
| Notebooks | [`nb_fhir_ingest.Notebook/`](../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/) | [Notebooks CODE.md](notebooks/CODE.md) | 真实 Git Native 业务 Notebook 已有完整代码并完成云端双格式读回；正式业务 Notebook Runtime / FHIR→Delta E2E 仍 HALT，未验收 |
| Environments | [`env_healthcare.Environment/`](../../../azure-fabric/workspaces/healthcare-omop/env_healthcare.Environment/) | [Environments CODE.md](environments/CODE.md) | env_healthcare 中 Wheel 0.1.3 已发布且 Spark 4.1 真实 Import PASS；正式 G4 Silver 与 G5 Source/P1 只读验收有独立证据，Candidate/Gold Pipeline E2E 尚未完成 |
| Lakehouse | [`lh_omop_analytics.Lakehouse/`](../../../azure-fabric/workspaces/healthcare-omop/lh_omop_analytics.Lakehouse/) | [Lakehouse native files](../../../azure-fabric/workspaces/healthcare-omop/lh_omop_analytics.Lakehouse/lakehouse.metadata.json) | Native 元数据导出本身不证明 Delta；G4 Silver 与 G5 Source Readonly 的受控业务读回另见相应 OpenSpec，不能外推 Gold E2E |
| Warehouse (`healthcare-omop` Workspace-only actual item) | [`omop-cdm-5.4/`](../../../azure-fabric/warehouse/omop-cdm-5.4/) · [`omop-foundation/`](../../../azure-fabric/warehouse/omop-foundation/) | [Warehouse CODE.md](warehouse/CODE.md) | Existing physical `dw-omop-5.4` Warehouse GUID `7a6d08da-278d-4603-8a3b-28640110984c` in same Workspace. F0 schema 39/432 and F1 Vocabulary 9/9 true SQL readback PASS; these are **SQL/Writer sources, not a `.Warehouse/` Git Native Item**. Protected from Git UpdateFromGit; Gold COMMITTED still not done |
| Pipelines | [`pl_fhir_ingest.DataPipeline/`](../../../azure-fabric/workspaces/healthcare-omop/pl_fhir_ingest.DataPipeline/) | [Pipelines CODE.md](pipelines/CODE.md) | 原生 Pipeline 已包含 1 个 TridentNotebook Activity；默认 HALT，未执行业务数据管道 |

## 2026-11-02 Git-first Notebook 实测（未来 Agent 必读）

新原生 Notebook **Git PR → main → GitHub Actions → Fabric UpdateFromGit → 独立代码/Environment 读回 → Spark 4.1/Wheel 0.1.1 导入 → 受控 Git 原生删除** 已全部实测 PASS。全过程证据和踩坑（尤其 `Added` 可能没有 `fileChanges`、运行后 Local Modified 与一次性安全删除）见 [Notebook Git Authoring Runbook](notebooks/FABRIC-GIT-AUTHORING-RUNBOOK.md) 与 [OpenSpec 验收](../../../openspec/changes/fabric-native-notebook-git-onboarding/tasks.md)。不能把本次创建运行 Smoke 当作正式 `nb_fhir_ingest` 的 FHIR/Delta 业务验收；业务 HALT 仍在。

## 跨组件依赖与源码边界

- [Self-Runner Azure-Infra-TF Workflow](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra.yaml) 正式执行 `fabric-workspace/<workspace_name>/<resource_type>/`，而 [Azure-Infra-Shared-TF](https://github.com/JohnZhang-DataForge/Self-Runner/blob/main/.github/workflows/azure-infra-shared.yaml) 独立执行 `shared-infra/storage/`。旧 `components/` 路由已经停用；Storage Plan 真实成功，Workspace Plan 因 Runner 缺 Capacity GUID 在预检阶段阻断。
- Terraform [Notebook 安全 Bootstrap](../../../azure-fabric/infra-terraform/modules/notebook/definitions/notebook-content.py) 和 [Pipeline Fail Activity](../../../azure-fabric/infra-terraform/modules/data-factory/definitions/pipeline-disabled.json) **归 Terraform 管理**；所有 Root/Module、Provider 和 IAM 文件请参阅 [Terraform CODE.md](infra-terraform/CODE.md)，此处不复制整张 Terraform 文件表。
- 本地只读 OMOP Exporter、不可变 Manifest、云端 Delta Loader、独立对账尚待开发；过去空的 `exporter/` 和 `tests/` 占位已删除，未来源码归属须依据真实运行位置另行确定。
- Terraform State、已有 Workspace/Blob/Entra 角色以及 Fabric Item GUID 应单独核验。历史七 Root Plan-only [验收记录](infra-terraform/ARCHITECTURE.md#verified-plan-evidence)不代表云端业务 E2E。

## Lakehouse 根级 Native 文件完整 CODE Map

| 原生源码文件 | 用途 |
| --- | --- |
| [lh_omop_analytics.Lakehouse/.platform](../../../azure-fabric/workspaces/healthcare-omop/lh_omop_analytics.Lakehouse/.platform) | 原生 Item 元数据，保留现有 ID |
| [lh_omop_analytics.Lakehouse/alm.settings.json](../../../azure-fabric/workspaces/healthcare-omop/lh_omop_analytics.Lakehouse/alm.settings.json) | 原生设置 |
| [lh_omop_analytics.Lakehouse/lakehouse.metadata.json](../../../azure-fabric/workspaces/healthcare-omop/lh_omop_analytics.Lakehouse/lakehouse.metadata.json) | Lakehouse 元数据；不代表业务数据已经验收 |
| [lh_omop_analytics.Lakehouse/shortcuts.metadata.json](../../../azure-fabric/workspaces/healthcare-omop/lh_omop_analytics.Lakehouse/shortcuts.metadata.json) | 原生 Shortcut 定义 |

## CODE.md 维护要求

Fabric Notebook/Pipeline 新增、删除、移动或改名源码时，**同一 PR** 修改所属 [Notebooks CODE](notebooks/CODE.md) 或 [Pipelines CODE](pipelines/CODE.md)，使用现有 CODE-map CI 验证。Terraform Root/Module、Provider、权限和主要执行入口改变时同步更新 [Terraform CODE](infra-terraform/CODE.md) 并审查 IAM/State/Import；现有 CI **不保证逐一覆盖每个 .tf 文件**。

Azure/Fabric 的 README/CODE/技术说明都在 `documents/systems/azure-fabric/`；源码区只保留真正的程序、Terraform 配置、模板以及 Fabric Item 生成的机器可读元数据，不维护第二份说明性文档。

## Retired johnzhang-test publisher (2026-10-31)

The old `johnzhang-test` native Notebook/Pipeline Smoke items, `trial_smoke_publisher.py`, offline tests and static workflow were removed from current Git after the final Fabric-native ADR. Prior sources remain in [fixed Git history](https://github.com/JohnZhang-DataForge/healthcare-data-platform/tree/e4640eb4ce4edd8570ca60c9ad2c1b6152941743/azure-fabric/workspaces/johnzhang-test). Self-Runner PR #350 separately retired the executable test workflows. This **does not mean the previously Terraform-applied test Workspace/Lakehouse has been destroyed**; its state-aware retirement remains pending. Do not re-use these test items for `healthcare-omop`.

## OpenLineage compatibility adapter (offline candidate)

**唯一文档 Owner**：[OpenLineage README](openlineage/README.md) · [CODE](openlineage/CODE.md) · [Publisher Protocol](openlineage/PUBLISHER.md)。

- [Candidate Listener config](../../../azure-fabric/openlineage/compatibility.py) · [Offline tests](../../../.github/quality/tests/azure-fabric/openlineage/test_compatibility.py) · [compatibility/authorization notes](openlineage/README.md). Scala 2.12 local and Scala 2.13 Fabric artifacts are not interchangeable. This source has no live Fabric test authorization; current Fabric Notebook HOLD remains.
## Immutable OpenLineage Blob Publisher (offline only)

- [Publisher entrypoint](../../../azure-fabric/openlineage/publisher.py) · [Fake Azure and recovery tests](../../../.github/quality/tests/azure-fabric/openlineage/test_publisher.py) · [publisher protocol](openlineage/PUBLISHER.md). Independently verified immutable event readback before committed Manifest; Azure live operations unapproved.

## 历史 P2 Notebook 开发阶段（2026-10-31 记录；非当前云端实时状态）

**2026-10-31 更新：**P2 唯一业务逻辑已迁入 Fabric Git Native Notebook [notebook-content.py](../../../azure-fabric/workspaces/healthcare-omop/nb_fhir_ingest.Notebook/notebook-content.py)。下列开发文件只作为离线加载/安全检查/测试工具，不能单独发布为第二个 Notebook 或 Wheel。正式发布仍需 Environment Publish 与独立云验收。

| 源码文件 | 职责 |
| --- | --- |
| [fhir_ingest_notebook.py](../../../azure-fabric/notebook-development/fhir_ingest_notebook.py) | 离线兼容导入 Native Notebook；不含第二套业务实现 |
| [native_item_readiness.py](../../../azure-fabric/notebook-development/native_item_readiness.py) | Fabric 原生 `.platform` 类型/名称/非零 ID 检查；导出成功仍 HOLD runtime exit 2 |
| [test_notebook_offline.py](../../../.github/quality/tests/azure-fabric/notebook/test_notebook_offline.py) | 真实 PySpark Schema/关联和负向离线测试 |
| [README.md](notebooks/GIT-FIRST-OFFLINE-VALIDATION.md) | 未发布 Notebook 实施边界和执行安全说明 |
| [fabric-fhir-notebook-offline.yml](../../../.github/workflows/fabric-fhir-notebook-offline.yml) | GitHub-hosted 离线 Wheel 精确 SHA/PySpark 负向 CI |


## Git-to-Fabric event-driven deployment trigger

- [Healthcare main push workflow](../../../.github/workflows/fabric-git-deploy.yml) — GitHub native Notebook/Pipeline source changes start a guarded trigger (no Azure/Fabric token in this public repo).
- [GitHub Actions dispatcher](../../../.github/quality/scripts/fabric_git_dispatch.py) — GitHub Actions workflow_dispatch to the private Self-Runner, pinned to exact Healthcare main SHA; no retry or cloud mutation.
- [Dispatcher offline tests](../../../.github/quality/tests/test_fabric_git_dispatch.py) — validates repo/main/SHA guards, fixed destination and secret-safe error handling.
- Private Self-Runner continues to own the Fabric OIDC, UpdateFromGit reconciliation, canonicalization analysis and independent deployed-definition readback. This trigger does not grant Environment Publish, Spark or Delta execution.


## P2 OpenLineage 的唯一技术文档所有者

- [OpenLineage README](openlineage/README.md) — 兼容性、Scala/Spark 版本、Fabric listener HOLD 和独立授权试验流程。
- [OpenLineage CODE](openlineage/CODE.md) — 当前兼容适配器与 Publisher 业务源码位置、以及 P3 已迁入的集中回归测试位置；保留业务源码，不重复实现。
- [Immutable Blob Publisher Protocol](openlineage/PUBLISHER.md) — 完整不可变对象、Manifest-last、无敏感信息和 Reader/Publisher 安全边界。


## P4 源码辅助程序保留结论（2026-11-04）

- [fhir_ingest_notebook.py](../../../azure-fabric/notebook-development/fhir_ingest_notebook.py) 只有 **17 行**，通过 `importlib` 按确定路径加载唯一 Git Native Notebook，并供 8 个已迁移测试中的多组作为兼容导入入口；它**不是第二个 ETL 实现**。搬到 `.github/quality/scripts/` 会改变模块导入、`PYTHONPATH` 和 Git Native 源码定位，当前无收益，保留原路径。
- [native_item_readiness.py](../../../azure-fabric/notebook-development/native_item_readiness.py) **63 行**，供 Native Contract/PySpark 离线测试及 [Fabric Notebook Offline Workflow](../../../.github/workflows/fabric-fhir-notebook-offline.yml) 直接调用（预期 exit 2 / HALT）。将其迁移需同步修改 Workflow 和模块相对路径，既无消除重复实现的收益，也会扩大发布风险；保持原位。
- **业务 Owner 冻结**：`azure-fabric/workspaces/healthcare-omop/` 继续包含真实 Notebook/Pipeline/Environment/Lakehouse Native Git Item；`azure-fabric/warehouse/` 是 CDM/Identity/Writer SQL 和 Python 源码（非 Git Native Warehouse）；`azure-fabric/openlineage/` 是 Publisher/Compatibility 业务实现。只有离线 **test_*.py** 归 `.github/quality/tests/azure-fabric/`。本阶段不创建 `src/` 镜像树、另一个 Wheel 或假 Warehouse Item。
