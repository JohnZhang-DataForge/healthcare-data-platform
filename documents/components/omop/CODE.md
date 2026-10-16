---
status: active
scope: omop-apps-source-map
last_verified: 2026-10-16
source_sha: d019429332e794e412426cf9c5053bafa043c05e
---

# OMOP Writer / Visit CDM — CODE / 源码导航

> 本页是该组件的**唯一源码地图**。基于上述 Git SHA 的源码和功能边界分类；不重复当前项目状态或运维 Runbook。组件概览见 [README.md](README.md)，运行安全门槛见 [Safe Operations](../../operations/SAFE-OPERATIONS.md)。

## 当前 NEW_ONLY Writer、审计与回滚辅助

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`audit_second_new_only_ready.py`](../../../apps/omop_writer/audit_second_new_only_ready.py) | 历史 NEW_ONLY S3/PG 提交前只读审计 |
| [`build_s3_rollback_plan.py`](../../../apps/omop_writer/build_s3_rollback_plan.py) | 已固定批次的只读 Rollback 计划生成 |
| [`commit_new_only_batch_once.py`](../../../apps/omop_writer/commit_new_only_batch_once.py) | 历史固定批次受控原子 COMMIT；绝非通用执行器 |
| [`dynamic_new_only_commit.py`](../../../apps/omop_writer/dynamic_new_only_commit.py) | 基于已验收路径生成动态原子事务 SQL，不执行提交 |
| [`fenced_joint_rollback.py`](../../../apps/omop_writer/fenced_joint_rollback.py) | 同事务 Fencing ROLLBACK 诊断 |
| [`generate_fenced_s3_rollback_sql.py`](../../../apps/omop_writer/generate_fenced_s3_rollback_sql.py) | 真实 S3 输入的 Fencing Rollback SQL 生成 |
| [`generate_second_new_only_fenced_rollback.py`](../../../apps/omop_writer/generate_second_new_only_fenced_rollback.py) | 历史第二批 Fenced Writer 回滚语句生成 |
| [`joint_s3_rollback.py`](../../../apps/omop_writer/joint_s3_rollback.py) | Person/Visit 联合诊断回滚；注意 Sequence 副作用 |
| [`new_only_airflow_writer.py`](../../../apps/omop_writer/new_only_airflow_writer.py) | Airflow KPO 调用的受控 NEW_ONLY 原子 Writer |
| [`precommit_gate.py`](../../../apps/omop_writer/precommit_gate.py) | Batch/Person/Visit/外键/数据库来源冲突只读 Precommit Guard |
| [`verify_real_postgres_readonly.py`](../../../apps/omop_writer/verify_real_postgres_readonly.py) | PG cdm_reader 权限和 Precommit 只读验证 |

## 历史 Visit Candidate / ID Map / CDM 核验

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`candidate_to_cdm_preflight.py`](../../../apps/task003/candidate_to_cdm_preflight.py) | 历史 Visit Candidate → CDM Spark/列校验 |
| [`verify_cdm_materialization_preflight.py`](../../../apps/task003/verify_cdm_materialization_preflight.py) | 历史 CDM Materialization 预检证据核实 |
| [`verify_committed_cdm_visit_materialization.py`](../../../apps/task003/verify_committed_cdm_visit_materialization.py) | 历史 Visit CDM 已提交持久化核验 |
| [`verify_committed_visit_id_mapping.py`](../../../apps/task003/verify_committed_visit_id_mapping.py) | 历史 Visit ID Map 提交结果核验 |
| [`verify_visit_id_allocation_recovery.py`](../../../apps/task003/verify_visit_id_allocation_recovery.py) | 历史 ID 分配恢复证据核验 |
| [`verify_visit_id_allocation_rehearsal.py`](../../../apps/task003/verify_visit_id_allocation_rehearsal.py) | 历史 ID 分配演练证据核验 |
| [`verify_visit_id_pre_mutation_gate.py`](../../../apps/task003/verify_visit_id_pre_mutation_gate.py) | 历史 Visit ID 更新前安全门 |
| [`verify_visit_id_readonly_preflight.py`](../../../apps/task003/verify_visit_id_readonly_preflight.py) | 历史 Visit ID Map 只读预检 |
| [`visit_candidate_rules.py`](../../../apps/task003/visit_candidate_rules.py) | 历史 Encounter 到 Visit Candidate 的纯规则 |

## 历史固定批次 CDM Loader 与事务接口

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`cdm_runtime_cli.py`](../../../apps/task004/cdm_runtime_cli.py) | 历史 CDM Plan 只读 CLI |
| [`step04a_compare_source_postgres_readonly.py`](../../../apps/task004/step04a_compare_source_postgres_readonly.py) | 历史 S3 Parquet / PG 来源键只读对账 |
| [`step04c_person_runner.py`](../../../apps/task004/step04c_person_runner.py) | 历史固定批次 Person 执行器；可能提交数据库 |
| [`step04c_person_sql_builder.py`](../../../apps/task004/step04c_person_sql_builder.py) | 历史固定批次 Person 事务 SQL Builder |
| [`step04d_visit_runner.py`](../../../apps/task004/step04d_visit_runner.py) | 历史固定批次 Visit 执行器；可能提交数据库 |
| [`step04d_visit_sql_builder.py`](../../../apps/task004/step04d_visit_sql_builder.py) | 历史固定批次 Visit 事务 SQL Builder |
| [`task004_step04b_replay_contract.py`](../../../apps/task004/task004_step04b_replay_contract.py) | 历史 Batch 幂等和重放策略纯模拟 |

## 关联入口

[Writer Dockerfile](../../../images/new-only-omop-writer/Dockerfile) · [Writer Contract](../../../contracts/omop-writer/writer-batch-identity-v1.json) · [Writer Tests](../../../tests/omop_writer/) · [SQL 源目录](../../../sql/)

`commit_new_only_batch_once.py`、`step04c_person_runner.py`、`step04d_visit_runner.py` 包含历史受控 COMMIT 路径，绝不能当成通用执行器。SQL 渲染、只读预检与真实 Commit 不是同一权限；当前 Person/Visit 的完成不代表 Condition 已入库。

## OMOP Writer Batch Identity Contract

| 源文件 | 角色 / 安全边界 |
| --- | --- |
| [`writer-batch-identity-v1.json`](../../../contracts/omop-writer/writer-batch-identity-v1.json) | Legacy 与 NEW_ONLY Writer 身份版本/Batch/Manifest 兼容协议；不授权 Commit |

## Person / Visit SQL 与历史只读核验

| 源文件 | 角色 / 安全边界 |
| --- | --- |
| [`person-upsert.sql`](../../../sql/task002/person-upsert.sql) | 业务 DML，需要授权：历史 Person Stage → CDM Person UPSERT |
| [`visit-id-map-foundation.sql`](../../../sql/task003/visit-id-map-foundation.sql) | 历史 Visit ID Map Foundation/结构校验；运行前确认 DDL/DML 实际影响 |
| [`visit-mapping-baseline.sql`](../../../sql/task003/visit-mapping-baseline.sql) | 只读：Visit ID Map、Person/Visit 基线摘要 |
| [`step04a-readonly-map-inventory.sql`](../../../sql/task004/step04a-readonly-map-inventory.sql) | 只读：CDM / ID Map 聚合清单 |
| [`step04a-readonly-schema-inventory.sql`](../../../sql/task004/step04a-readonly-schema-inventory.sql) | 只读：CDM/ETL Schema、表、索引检查 |
| [`step04c-batch-schema-v1-authorized.sql`](../../../sql/task004/step04c-batch-schema-v1-authorized.sql) | DDL，需要授权：历史固定基线 Batch Ledger/Stage/Commit 结构迁移 |
| [`step04c-batch-schema-v1-readback.sql`](../../../sql/task004/step04c-batch-schema-v1-readback.sql) | 只读：历史 Batch 结构迁移结果检查 |
| [`step04c-person-readonly-readiness.sql`](../../../sql/task004/step04c-person-readonly-readiness.sql) | 只读：历史 Person Commit 预检 |
| [`step04d-visit-readiness-readonly.sql`](../../../sql/task004/step04d-visit-readiness-readonly.sql) | 只读：历史 Visit Commit 预检 |
| [`step04e-joint-reconciliation-readonly.sql`](../../../sql/task004/step04e-joint-reconciliation-readonly.sql) | 只读：历史 Person/Visit 同批联合对账 |

**执行区别**：`person-upsert.sql` 是真实 DML，`step04c-batch-schema-v1-authorized.sql` 是有历史固定环境前提的 DDL，不允许不审查就重放。其它 SQL 也应核对角色与事务边界。现在受控 NEW_ONLY Writer 的核心事务 SQL 还由 Python 动态生成；这个静态 SQL 清单不能代表完整 Writer 行为。

## OMOP / CDM Writer 容器镜像

| 源文件（直接链接） | 用途与运行边界 |
| --- | --- |
| [`Dockerfile`](../../../images/new-only-omop-writer/Dockerfile) | 已验收 NEW_ONLY Person/Visit 原子 Writer：固定基镜像 Digest + 对齐的 Airflow Legacy CDM 模块 |
| [`Dockerfile`](../../../images/task004-cdm-runtime/Dockerfile) | 历史 CDM Plan / S3 数据读取和 PG SQL 渲染基础镜像；默认只读 CLI，不等于原子业务 Commit |

**关键风险**：已验收的 Writer 镜像使用固定的历史 CDM Base Digest，同时显式 COPY 与 NEW_ONLY Batch 身份匹配的 `task004_cdm_materialization_plan.py`、`task004_cdm_dynamic_source.py`、`task004_cdm_dynamic_adapters.py`、`task004_cdm_dynamic_pg_writer.py` 等模块。之前继承基镜像中的过期逻辑会导致 `BLOCKED=batch_id`；修改任何镜像 COPY/BuildContext/Entrypoint、Python 模块或 Base Digest 前须做契约测试、镜像 Smoke、不可变 Digest 发布、Consumer Pin 和实际运行后置证据。镜像 Build PASS 不等于 PostgreSQL COMMIT。

## 历史 Shell / 脚本导航（由 omop 组件负责）

> 本清单是历史 Step Shell 的**代码索引，不是按顺序执行的 Runbook**。这些文件可能使用固定 Git SHA/Batch ID、操作 S3/PG/K8s、修改仓库源码或生成本地报告；任何执行须先读脚本全文并核对 [Safe Operations](../../operations/SAFE-OPERATIONS.md)。新脚本必须按组件/能力命名，不能新增 `taskNNN` 路径。

## 历史 task002（3 个入口）

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`06-capture-person-cdm-baseline.sh`](../../../scripts/task002/06-capture-person-cdm-baseline.sh) | [PREPARE / may write] 历史 TASK002 capture person CDM baseline 脚本 |
| [`06b-load-person-stage.sh`](../../../scripts/task002/06b-load-person-stage.sh) | [EXECUTE / review] 历史 TASK002 load person stage 脚本 |
| [`07-upsert-person-cdm-idempotency.sh`](../../../scripts/task002/07-upsert-person-cdm-idempotency.sh) | [HIGH / review] 历史 TASK002 upsert person CDM idempotency 脚本；可能操作 PostgreSQL 业务持久化，禁止重放已提交批次 |

## 历史 task003（32 个入口）

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`01-discover-visit-occurrence.sh`](../../../scripts/task003/01-discover-visit-occurrence.sh) | [CHECK / verify effects] 历史 TASK003 discover visit occurrence 脚本 |
| [`02-discover-visit-mapping-foundation.sh`](../../../scripts/task003/02-discover-visit-mapping-foundation.sh) | [CHECK / verify effects] 历史 TASK003 discover visit mapping foundation 脚本 |
| [`05-prepare-visit-omop.sh`](../../../scripts/task003/05-prepare-visit-omop.sh) | [PREPARE / may write] 历史 TASK003 prepare visit OMOP 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05a-verify-visit-omop-input.sh`](../../../scripts/task003/05a-verify-visit-omop-input.sh) | [CHECK / verify effects] 历史 TASK003 verify visit OMOP input 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`05b-inspect-visit-database.sh`](../../../scripts/task003/05b-inspect-visit-database.sh) | [CHECK / verify effects] 历史 TASK003 inspect visit database 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`05b-prepare-visit-db-baseline.sh`](../../../scripts/task003/05b-prepare-visit-db-baseline.sh) | [PREPARE / may write] 历史 TASK003 prepare visit db baseline 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05c-create-visit-id-map.sh`](../../../scripts/task003/05c-create-visit-id-map.sh) | [PREPARE / may write] 历史 TASK003 create visit id map 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`05c-prepare-visit-id-map.sh`](../../../scripts/task003/05c-prepare-visit-id-map.sh) | [PREPARE / may write] 历史 TASK003 prepare visit id map 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`06a1-visit-id-allocation-baseline-discovery.sh`](../../../scripts/task003/06a1-visit-id-allocation-baseline-discovery.sh) | [LEGACY / review] 历史 TASK003 visit id allocation baseline discovery 脚本 |
| [`06a2-plan-visit-id-allocation.sh`](../../../scripts/task003/06a2-plan-visit-id-allocation.sh) | [CHECK / verify effects] 历史 TASK003 plan visit id allocation 脚本 |
| [`06a3-reconcile-visit-business-keys.sh`](../../../scripts/task003/06a3-reconcile-visit-business-keys.sh) | [CHECK / verify effects] 历史 TASK003 reconcile visit business keys 脚本 |
| [`06a4-prepare-visit-id-readonly-preflight-freeze.sh`](../../../scripts/task003/06a4-prepare-visit-id-readonly-preflight-freeze.sh) | [PREPARE / may write] 历史 TASK003 prepare visit id readonly preflight freeze 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`06a4-verify-visit-id-readonly-preflight.sh`](../../../scripts/task003/06a4-verify-visit-id-readonly-preflight.sh) | [CHECK / verify effects] 历史 TASK003 verify visit id readonly preflight 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`06a5-prepare-readonly-runner-snapshots.sh`](../../../scripts/task003/06a5-prepare-readonly-runner-snapshots.sh) | [PREPARE / may write] 历史 TASK003 prepare readonly runner snapshots 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`06b1-build-visit-id-mutation-contract.sh`](../../../scripts/task003/06b1-build-visit-id-mutation-contract.sh) | [PREPARE / may write] 历史 TASK003 build visit id mutation contract 脚本 |
| [`06b2-freeze-visit-business-key-snapshot.sh`](../../../scripts/task003/06b2-freeze-visit-business-key-snapshot.sh) | [PREPARE / may write] 历史 TASK003 freeze visit business key snapshot 脚本 |
| [`06b3-prepare-visit-id-pre-mutation-gate.sh`](../../../scripts/task003/06b3-prepare-visit-id-pre-mutation-gate.sh) | [PREPARE / may write] 历史 TASK003 prepare visit id pre mutation gate 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`06b3-verify-visit-id-pre-mutation-gate.sh`](../../../scripts/task003/06b3-verify-visit-id-pre-mutation-gate.sh) | [CHECK / verify effects] 历史 TASK003 verify visit id pre mutation gate 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`06b4a-prepare-visit-id-allocation-rehearsal.sh`](../../../scripts/task003/06b4a-prepare-visit-id-allocation-rehearsal.sh) | [PREPARE / may write] 历史 TASK003 prepare visit id allocation rehearsal 脚本；可能操作 PostgreSQL 业务持久化，禁止重放已提交批次 |
| [`06b4a-rehearse-visit-id-allocation.sh`](../../../scripts/task003/06b4a-rehearse-visit-id-allocation.sh) | [EXECUTE / review] 历史 TASK003 rehearse visit id allocation 脚本 |
| [`06b4a-verify-visit-id-allocation-rehearsal.sh`](../../../scripts/task003/06b4a-verify-visit-id-allocation-rehearsal.sh) | [CHECK / verify effects] 历史 TASK003 verify visit id allocation rehearsal 脚本；可能操作 PostgreSQL 业务持久化，禁止重放已提交批次 |
| [`06b4b-r1-prepare-visit-id-allocation-recovery.sh`](../../../scripts/task003/06b4b-r1-prepare-visit-id-allocation-recovery.sh) | [PREPARE / may write] 历史 TASK003 r1 prepare visit id allocation recovery 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`06b4b-r1-reconcile-failed-visit-id-allocation.sh`](../../../scripts/task003/06b4b-r1-reconcile-failed-visit-id-allocation.sh) | [CHECK / verify effects] 历史 TASK003 r1 reconcile failed visit id allocation 脚本 |
| [`06b4b-r1-verify-visit-id-allocation-recovery.sh`](../../../scripts/task003/06b4b-r1-verify-visit-id-allocation-recovery.sh) | [CHECK / verify effects] 历史 TASK003 r1 verify visit id allocation recovery 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`06b4b-r2-corrected-visit-id-allocation.sh`](../../../scripts/task003/06b4b-r2-corrected-visit-id-allocation.sh) | [HIGH / review] 历史 TASK003 r2 corrected visit id allocation 脚本；可能操作 PostgreSQL 业务持久化，禁止重放已提交批次 |
| [`06b4c-prepare-committed-visit-id-mapping.sh`](../../../scripts/task003/06b4c-prepare-committed-visit-id-mapping.sh) | [PREPARE / may write] 历史 TASK003 prepare committed visit id mapping 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`06b4c-verify-committed-visit-id-mapping.sh`](../../../scripts/task003/06b4c-verify-committed-visit-id-mapping.sh) | [CHECK / verify effects] 历史 TASK003 verify committed visit id mapping 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`06c2-candidate-to-cdm-column-preflight.sh`](../../../scripts/task003/06c2-candidate-to-cdm-column-preflight.sh) | [CHECK / verify effects] 历史 TASK003 candidate to CDM column preflight 脚本 |
| [`06c3-prepare-cdm-materialization-preflight.sh`](../../../scripts/task003/06c3-prepare-cdm-materialization-preflight.sh) | [PREPARE / may write] 历史 TASK003 prepare CDM materialization preflight 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`06c3-verify-cdm-materialization-preflight.sh`](../../../scripts/task003/06c3-verify-cdm-materialization-preflight.sh) | [CHECK / verify effects] 历史 TASK003 verify CDM materialization preflight 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`06c4e-prepare-committed-cdm-visit-materialization.sh`](../../../scripts/task003/06c4e-prepare-committed-cdm-visit-materialization.sh) | [PREPARE / may write] 历史 TASK003 prepare committed CDM visit materialization 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`06c4e-verify-committed-cdm-visit-materialization.sh`](../../../scripts/task003/06c4e-verify-committed-cdm-visit-materialization.sh) | [CHECK / verify effects] 历史 TASK003 verify committed CDM visit materialization 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |

## 源码维护约定

**新增、删除、重命名或移动本组件负责的 `apps/`、`contracts/`、`sql/`、`images/`、`kubernetes/` 或 `scripts/` 源文件，必须在同一个 PR 更新本 CODE.md。** CODE.md 只做导航，不能当作重新执行历史脚本的授权。历史 `taskNNN` 程序仍可能被 Docker COPY、Import 或冻结 Contract 引用；先看 [Legacy 重构计划](../LEGACY-CODE-REFACTOR-PLAN.md)。

