---
status: active
scope: omop-apps-source-map
last_verified: 2026-10-16
source_sha: e26d8032deaab8ae4cfdbc1d446eceb5d9dc8ac9
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

## 源码维护约定

**新增、删除、重命名或移动本组件负责的 `apps/` 源文件时，必须在同一个 PR 更新此 CODE.md。** CODE.md 只做导航，不能当作重新执行历史脚本的授权。历史 `taskNNN` 程序仍可能被 Docker COPY、Import 或冻结 Contract 引用；先看 [Legacy 重构计划](../LEGACY-CODE-REFACTOR-PLAN.md)。

