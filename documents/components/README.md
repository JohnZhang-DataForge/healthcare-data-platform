---
status: active
scope: component-catalog
last_verified: 2026-10-16
source_sha: 2c85b485381a72425506829fd321d93b164a231d
---

# Local Pipeline — 组件地图

> **STEP05 的组件说明入口**：基于 Main `2c85b485381a72425506829fd321d93b164a231d` 的静态源码与现有 TASK004 Final E2E 验收。按**长期功能**而非 Task/Step 组织知识；没有执行任何 Runtime 操作。项目总体 CURRENT/NEXT 见 [PROJECT-STATUS](../status/PROJECT-STATUS.md)，命名硬规则见 [Code Naming](../development/CODE-ORGANIZATION-AND-NAMING.md)。

| 组件 | 权威组件说明 | 当前源码与边界 |
| --- | --- | --- |
| Synthea Producer | [Synthea](synthea/README.md) | `apps/synthea/new_only/`、`images/synthea-new-only/`，独立 Generator |
| Landing / Manifest / Claim | [Landing](landing/README.md) | `apps/landing_discovery/`、`apps/landing_claim/`，不可变 Batch + Claim Guard |
| Airflow Orchestration | [Airflow](airflow/README.md) | `airflow/dags/`，手工受控 NEW_ONLY Consumer 与独立 Discovery |
| Spark Canonical / DQ | [Spark](spark/README.md) | `spark/apps/person/`、`spark/apps/visit/`、`spark/common/` |
| OMOP Writer / PostgreSQL | [OMOP](omop/README.md) | `apps/omop_writer/`、`sql/`，原子事务、Mapping、Reconciliation |

**横切边界**：Portal/Marquez 可观测性与 Azure PG→Blob→Fabric→OneLake 不属于这些模块的实际数据处理逻辑；详细组件说明在 STEP06，当前总设计见 [System Overview](../architecture/SYSTEM-OVERVIEW.md)。

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
- 新增 Condition 时直接进入 `spark/apps/condition/` 等功能目录；**禁止** `task005` 命名的源文件/测试/镜像/正式脚本。
- 现在的旧 `apps/task004`、`airflow/dags/task004_cdm_*.py`、`spark/apps/task004/` 等**不能直接删/全仓重命名**，实际依赖见 [Legacy Refactor Plan](LEGACY-CODE-REFACTOR-PLAN.md)。
- 本轮按组件重建的是**文档架构和今后代码命名治理**；真实代码迁移是独立 PR/测试/部署，不会修改已关闭的 TASK004 E2E 事实。
