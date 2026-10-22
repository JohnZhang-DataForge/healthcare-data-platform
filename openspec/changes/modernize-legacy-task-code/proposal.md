# Proposal

> **2026-10-22 用户确认的新决策（PLANNED，未实施）**：将此前“兼容优先、旧接口永久冻结”的 R2–R5 渐进方案，改为 **Clean Slate / Fresh-State Component Naming Migration**。本次 PR **仅更新 OpenSpec 规划和拟采用的 Delta Spec**，不触碰业务代码、数据库、S3、Airflow、Kubernetes、GHCR 或 Self-Runner 运行资源。原来的 2026-10-16/18 设计及其历史验收记录保留在 Git 历史中，但不再充当本 Change 的执行顺序。

## Why

Healthcare Local Data Platform 已完成 `local-data-platform/` 目录搬迁、批准范围内的历史安装器清理和新的 Synthea → S3 → Airflow → Spark → OMOP Writer → PostgreSQL 真实 E2E 验收。现存 `task001`–`task004` / `stepNNN` 命名来自开发阶段，而非组件边界，并散布于模块、Shell、SQL、Docker、DAG、GHCR、Kubernetes、Workflow、测试和持久化接口，继续扩展 Portal/多来源系统会放大维护成本。

**当前决策的前提**：现有 Local DP OMOP/ETL 和 Landing 数据为可再生的开发合成数据，用户明确允许放弃这批旧业务数据与历史运行身份。无需旧业务数据迁移、旧 DAG 历史关联和新旧持久化表的兼容桥接。系统要能凭 Git 的正式代码与受控环境配置，在既有基础设施上从空业务状态重新初始化并通过新的 E2E。

冻结规划基线：Healthcare Main `b99c5e8d4f3e5e4481facde3f7196569645125fb`、Self-Runner Main `79464c92cf244508d81c99fc25be9cd90820bad1`（2026-10-22 只读获取）。Healthcare 未截断 Git Tree 中 `local-data-platform/` **360** 个 tracked files，其中 **234** 个文件路径含 `task001`–`task004`，107 个测试文件。路径计数**不等于**内容引用数、改名操作数或 Live 消费者闭包；执行前须重扫最新 SHA。

## What Changes

- 以组件/领域/职责命名替代 `task001`–`task004` 和作为实现步骤的 `stepNNN`，覆盖维护中的源码目录、Python module/import、Shell/测试、SQL、Docker COPY/Entrypoint、CI、跨仓 Self-Runner、镜像包名、K8s 名称、Airflow DAG ID/资源和可再生 PG 业务表、Schema、函数等。
- 初步职责映射：`task001 → intake / landing`，`task002 → person`，`task003 → encounter / visit / omop_writer`，`task004 → orchestration / landing / omop_writer`；**不是四个目录机械对调**。精确旧→新标识及消费者由实施前的双仓矩阵冻结，避免名字冲突、职责混淆。
- **Fresh-state 而非 data migration**：优先创建隔离的新业务状态（同一 PostgreSQL 实例内独立的开发业务数据库，或经证实等价的完整 Schema 隔离；包括 CDM、ETL、Ledger、Claim、Checkpoint、ID Map、Sequence、Roles/Grants），独立生成新 S3 Batch/Manifest 和新 DAG；不复制旧表记录、不迁移旧 Airflow Run、不重放旧 Batch。
- 新镜像 Clean Build，完成完整 E2E 与同 Batch 幂等/失败闭锁，验证新 DAG 的调度和真实镜像来源后，才分对象删除已确认无消费者的旧业务表、旧 DAG 元数据、旧 S3 测试对象及旧 K8s/GHCR 业务资源。
- 沿用现有 `apps/`、`airflow/`、`spark/`、`scripts/`、`sql/`、`tests/`、`images/`、`kubernetes/` 等架构；**保持 Manifest 身份验证、Writer Atomic Commit、Fencing、Reservation、Claim、重试/幂等语义**，不借改名重写业务模型。
- 以一个 Active OpenSpec Change 承载规范、实施 Tasks、PR 和证据；修订旧 `modernize-legacy-task-code` 而不新建重复 Change。和 `relocate-local-data-platform` 仅按各自范围独立收口，不重写历史 PASS/FAIL。

## Capabilities

### New Capabilities

- `clean-slate-local-dp-migration`：定义可复现的旧→新命名一致性、独立新业务状态初始化、双 DAG 防重复、端到端验收和受控旧状态退役。

### Modified Capabilities

- 维护中组件代码和运行资源从历史 Task/Step 编号名称切换到职责名称；旧数据/旧标识兼容不再属于本**开发业务环境**的目标要求。现有数据质量与事务安全行为保持不变。

## Impact

涉及 Healthcare 与 Self-Runner 源码消费者、Airflow GitSync/DagBag、K8s RBAC/ServiceAccount、8 个当前业务镜像父子构建关系、GHCR 引用、PostgreSQL OMOP/ETL/Claim、S3 Landing 路径、组件 CODE.md、CI、Portal 的潜在 DAG/Lineage 引用。

**明确不在本 Change 清理范围**：PostgreSQL 实例/PG14 Marquez、Airflow Metadata DB 整库、SeaweedFS PVC/存储服务、Kubernetes 节点/集群、Spark/Airflow Operator、GitHub/Self-Runner Infrastructure、Secrets 的随意删除、Azure Blob/Fabric/OneLake、Terraform State、Portal 的其它数据和 Git 运行/验收历史。任何“可删除”均先核实精确资源所有权及真实消费者。若新旧系统无法完全隔离，必须先排他停旧、再重建指定的开发业务状态，不假装能平行双写。

**授权边界**：用户在本轮批准的是迁移方向和可放弃旧**合成业务数据**的原则，本方案 PR 不执行任何有副作用操作。实际共享环境 reset / drop / S3 delete / DAG 操作仍按受控实施 Task 核对目标、空闲情况和批准范围；失败或状态未知时停止盲目重跑。**无生产迁移/向后兼容 SLA**；唯一接受门槛是新命名平台的真实全链路成功与完整来源证据。
