---
status: active
scope: component-catalog
last_verified: 2026-11-05
source_sha: 2c85b485381a72425506829fd321d93b164a231d
---


**旧 Task 命名代码的业务导航与迁移边界：** [223 个文件 Git Blob 清单](../../engineering/development/LEGACY-TASK-GIT-INVENTORY-20261105.json) · [19 组功能 Owner 与迁移门禁](../../engineering/development/LEGACY-TASK-COMPONENT-MIGRATION-MAP.md)。这些是静态规划，现有 Airflow/Docker/PG/Workflow 仍可能引用旧路径，**不得直接删除或批量改名**。
# Local Pipeline — 组件地图

> **2026-10-18 源码目录迁移后导航更新**：物理源码位置已由 PR #225 调整，本页引用新路径；运行逻辑尚未经新位置回归验证，旧 STEP05 组件分类与历史业务验收不因此变更。
>
> **STEP05 的组件说明入口**：基于 Main `2c85b485381a72425506829fd321d93b164a231d` 的静态源码与现有 TASK004 Final E2E 验收。按**长期功能**而非 Task/Step 组织知识；没有执行任何 Runtime 操作。项目尚在实施的任务见 [Active OpenSpec](../../../openspec/changes/) 的对应 `tasks.md`（[PROJECT-STATUS](../../engineering/status/PROJECT-STATUS.md) 仅导航），命名硬规则见 [Code Naming](../../engineering/development/CODE-ORGANIZATION-AND-NAMING.md)。

| 组件 | 权威组件说明 | 当前源码与边界 |
| --- | --- | --- |
| Clinical external FHIR/OIE producer | [Clinical Producers](clinical-producers/README.md) · [Current source CODE](synthea/CODE.md) | `local-data-platform/apps/clinical_producers/oie/`、`images/oie/`、`kubernetes/manifests/oie/`；ADT A01 mapping / OIE 4.7.0 lifecycle，区别于 Synthea Generator |
| **HL7 local Parser / Delta Staging / dbt Candidate** | [HL7 Component](hl7/README.md) · [CODE](hl7/CODE.md) | `local-data-platform/spark/apps/hl7/`：仅已审核的 OIE V2 来源 Profile，独立本地 Spark/Delta + dbt，输出 Candidate，不写正式 Silver/Gold |
| Synthea Producer | [Synthea](synthea/README.md) · [CODE](synthea/CODE.md) | `local-data-platform/apps/synthea/new_only/`、`local-data-platform/images/synthea-new-only/`，独立 Generator |
| Landing / Manifest / Claim | [Landing](landing/README.md) · [CODE](landing/CODE.md) | `local-data-platform/apps/landing_discovery/`、`local-data-platform/apps/landing_claim/`，不可变 Batch + Claim Guard |
| Airflow Orchestration | [Airflow 组件说明](airflow/README.md) · [CODE 源码导航](airflow/CODE.md) | `local-data-platform/airflow/dags/`，手工受控 NEW_ONLY Consumer 与独立 Discovery |
| Spark Canonical / DQ | [Spark](spark/README.md) · [CODE](spark/CODE.md) | `local-data-platform/spark/apps/person/`、`local-data-platform/spark/apps/visit/`、`local-data-platform/spark/common/` |
| OMOP Writer / PostgreSQL | [OMOP](omop/README.md) · [CODE](omop/CODE.md) | `local-data-platform/apps/omop_writer/`、`local-data-platform/sql/`，原子事务、Mapping、Reconciliation |
| **OHDSI ATLAS3 / WebAPI3 (new private research consumer)** | [ATLAS CODE](atlas/CODE.md) | `local-data-platform/kubernetes/manifests/atlas/` 统一 K8s、`local-data-platform/images/atlas3-ui/` 构建镜像、`local-data-platform/atlas/` app/SQL；用户指定 `worker03`、`dw-atlas`，复用 PG17，不改变 OMOP Writer |

**横切边界（2026-11-05 架构对齐）**：[Portal / Marquez](../platform-portal/README.md) 是独立观测系统；[Azure/Fabric](../azure-fabric/README.md) 已经有单独的 **FHIR→Bronze→Canonical Silver→OMOP Gold** 开发主线，原 Local PG→Fabric 分析副本只是另一条尚未实现的产品路线，不能继续把整个 Fabric 定义为 PG 复制。两种 Runtime 各自拥有物理 Writer，不共享 PG/Fabric SQL 实现。权威：[总架构](../../architecture/SYSTEM-OVERVIEW.md) · [Canonical Medallion ADR](../../architecture/design/FABRIC-MEDALLION-CANONICAL-ADR-20261030.md) · [Shared Engine Owner](../../engineering/development/SHARED-DATA-ENGINE-STRUCTURE-AND-OWNERSHIP.md)。

**复用进度的真实边界**：Local CSV→Canonical→OMOP Person/Visit 已通过历史 PG17 原子 COMMIT/Replay 验证，但其生产 Spark/PG Mapper 仍保留 Local 原路径。唯一 Shared Wheel `healthcare_data_engine` 0.1.3 已经实现 FHIR→Canonical/OMOP Candidate 并部署于 Fabric；**Local 正式迁移到同一 Shared 实现尚未完成**。以后新增来源先实现专用 Adapter，再通过同一 Canonical Contract 和经审批的 Source Mapping Profile 进入共用业务层；逐模块抽纯函数并验证旧行为等价，不将旧 Writer 搬入 Shared、不增加第二个 Fabric Mapper。

## 新开发：OpenSpec Forward-Only（2026-11-05 起）

**历史保留，新任务统一 OpenSpec。** TASK001–TASK004 的既有源码、目录、已验收 Person/Visit 结果、Run/PR/Batch/Contract 与历史文档原样保留，不为采用 OpenSpec 追溯重建任务或迁移旧代码。历史 TASK005 Condition 仍是设计参考，不是当前开发状态；旧 TASK 文档不再写新的 CURRENT/NEXT。

新功能、其他 OMOP 域（如 Condition/Drug/Procedure/Measurement）、实质性代码行为变更、DAG/Writer/Contract/Runtime 配置改动：先核对最新 main 和开放 PR，按下表找到组件唯一 README/CODE、现行源码及合同；再查询 [Active OpenSpec Changes](../../../openspec/changes/) 是否已有该功能的业务 Change，**没有则先创建一个**，由其 `tasks.md` 独占 OPEN/DONE。关联 PR 使用 `OpenSpec-Change` 和 `OpenSpec-Task`，同 PR 更新 Tasks。不得另建 TASK006 文档或第二份平行任务表。

| 新能力 Owner | 读取的源码导航 | 现有代码根目录 / 新域应继承的职责 |
| --- | --- | --- |
| Source / Landing / Manifest / Claim | [Synthea CODE](synthea/CODE.md) · [Landing CODE](landing/CODE.md) | `local-data-platform/apps/synthea/`、`apps/landing_discovery/`、`apps/landing_claim/`；复用 Manifest/Claim Fence |
| Spark Canonical / Candidate / DQ | [Spark CODE](spark/CODE.md) | `local-data-platform/spark/apps/person/`、`apps/visit/` 与 `spark/common/`；新 Condition 可在 `spark/apps/condition/` 按功能增加源码（**尚未实施**） |
| PostgreSQL OMOP / Identity / Ledger / Commit | [OMOP CODE](omop/CODE.md) | `local-data-platform/apps/omop_writer/`、`local-data-platform/sql/`；禁止绕过现有事务、ID/FK 与幂等保护 |
| Airflow Orchestration | [Airflow CODE](airflow/CODE.md) | `local-data-platform/airflow/dags/`；新功能先隔离测试，不直接破坏已验收 Person/Visit Consumer |

历史 [TASK005 Condition 设计（只读 Git 快照）](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-005-CONDITION-DEVELOPMENT-PLAN-v1.0.zh-CN.md) 的 Source/FK/Vocabulary/Occurrence Key 等约束须结合当前代码与真实 Contract 重新核验；它所述旧 `tests/task005/`、`scripts/task005/`、`docs/tasks/` 已被新布局规则取代。所有新自动化测试位于 `.github/quality/tests/data-platform/<component>/`（组件名按实际 Owner），并随新增/迁移源码在**同一 PR** 更新组件唯一 CODE.md。

已有 [relocate-local-data-platform OpenSpec](../../../openspec/changes/relocate-local-data-platform/tasks.md) 继续专责旧目录迁移/兼容/清理的既定收尾；**不得**用它管理新增 Condition 等业务功能。OpenSpec/PR 的存在不等于授权 K8s/S3/PG 写入：真实新批次、Schema/COMMIT、历史 Batch replay 必须遵守 [Safe Operations](../../engineering/operations/SAFE-OPERATIONS.md)、实际资源互斥和独立读回。业务代码、固定执行标识、Legacy Contracts/测试在本次治理中均不修改。

## 组件职责与依赖方向

```text
Synthea Producer → S3 Landing + immutable manifest
                      ↓
                 Landing discovery + Claim
                      ↓
                 Airflow Consumer (orchestration only)
                      ↓
            Spark Person / Visit domain processing
                      ↓
          OMOP Writer (transaction, fencing, mapping)
                      ↓
                PostgreSQL OMOP
```

- Source Manifest、身份校验、Claim/Writer 闸门使用**一个明确的接口拥有者**；不再为 Task005 复制整套 Task004 实现。
- Airflow 仅编排/路由，Spark 负责数据加工，OMOP Writer 负责数据持久化；公共功能优先放在对应功能库，避免巨型 DAG 或巨型 Shell。
- 新增 Condition 时直接进入 `local-data-platform/spark/apps/condition/` 等功能目录；**禁止** `task005` 命名的源文件/测试/镜像/正式脚本。
- 现在已迁入 `local-data-platform/` 的旧 `apps/task004`、`airflow/dags/task004_cdm_*.py`、`spark/apps/task004/` 等**不能直接删/全仓重命名**，实际依赖见 [Legacy Refactor Plan](../../engineering/development/LEGACY-CODE-REFACTOR-PLAN.md)。
- 本轮按组件重建的是**文档架构和今后代码命名治理**；业务源码已通过物理迁移 PR #225 移至 `local-data-platform/`，但 Import、Docker、DAG、CI 与 Runtime 功能修复及验收仍须独立进行，不会修改已关闭的 TASK004 E2E 事实。
