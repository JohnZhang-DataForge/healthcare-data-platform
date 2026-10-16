---
status: active
scope: landing-apps-source-map
last_verified: 2026-10-16
source_sha: e26d8032deaab8ae4cfdbc1d446eceb5d9dc8ac9
---

# Landing / Discovery / Claim — CODE / 源码导航

> 本页是该组件的**唯一源码地图**。基于上述 Git SHA 的源码和功能边界分类；不重复当前项目状态或运维 Runbook。组件概览见 [README.md](README.md)，运行安全门槛见 [Safe Operations](../../operations/SAFE-OPERATIONS.md)。

## Landing Discovery 与 Claim/Fencing

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`batch_ledger.py`](../../../apps/landing_claim/batch_ledger.py) | PostgreSQL Claim 生命周期、身份与锁操作 |
| [`claim_discovered_inventory.py`](../../../apps/landing_claim/claim_discovered_inventory.py) | Discovery 到 Claim 的权限及 Allowlist Gate |
| [`lease_fence.py`](../../../apps/landing_claim/lease_fence.py) | 事务内 Claim Owner / Lease Fencing |
| [`verify_fencing_rollback.py`](../../../apps/landing_claim/verify_fencing_rollback.py) | 仅使用合成身份的 Fencing ROLLBACK 检验 |
| [`verify_rollback.py`](../../../apps/landing_claim/verify_rollback.py) | 合成 Claim 状态流转 ROLLBACK 检验 |
| [`run_airflow_scan.py`](../../../apps/landing_discovery/run_airflow_scan.py) | 供 Airflow KPO 使用的只读扫描入口与 XCom 摘要 |
| [`scan_ready_batches.py`](../../../apps/landing_discovery/scan_ready_batches.py) | 只读枚举与验证已发布 S3 READY Batch |

## 历史 Intake / Landing Resolver

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`resolve_verified_intake_file.py`](../../../apps/resolve_verified_intake_file.py) | 历史 TASK001 验证报告与源文件解析 |
| [`build_intake_manifest.py`](../../../apps/task001/build_intake_manifest.py) | 历史 Intake Manifest 文件构建 |
| [`landing_guard.py`](../../../apps/task001/landing_guard.py) | 历史 Landing Prefix / 写入路径防护 |
| [`resolve_verified_landing_file.py`](../../../apps/task004/resolve_verified_landing_file.py) | 历史 S3 Landing Manifest 和来源验证 |
| [`validate_new_only_v2_manifest.py`](../../../apps/task004/validate_new_only_v2_manifest.py) | NEW_ONLY v2 Manifest Reader 合同验证 |

## 历史 Encounter/Visit Raw 与 Processed 发布安全

| 实际源码文件 | 作用及使用边界 |
| --- | --- |
| [`build_encounter_raw_evidence.py`](../../../apps/task003/build_encounter_raw_evidence.py) | 历史 Encounter Raw 发布来源与结果证据 |
| [`build_visit_processed_dq.py`](../../../apps/task003/build_visit_processed_dq.py) | 历史 Processed Visit DQ 证据构建 |
| [`build_visit_processed_manifest.py`](../../../apps/task003/build_visit_processed_manifest.py) | 历史 Visit Processed APPROVED Manifest 构建 |
| [`build_visit_processed_runtime_bundle.py`](../../../apps/task003/build_visit_processed_runtime_bundle.py) | 历史 Visit Spark/ConfigMap 静态运行包构建 |
| [`build_visit_writer_reservation.py`](../../../apps/task003/build_visit_writer_reservation.py) | 历史 Visit 发布 Reservation 模板构建 |
| [`inspect_visit_processed_prefix.py`](../../../apps/task003/inspect_visit_processed_prefix.py) | 历史 Processed S3 Prefix 只读冲突检查 |
| [`issue_visit_processed_write_permit.py`](../../../apps/task003/issue_visit_processed_write_permit.py) | 历史单次写入 Permit 校验与签发 |
| [`plan_visit_processed.py`](../../../apps/task003/plan_visit_processed.py) | 历史不可变 Visit Processed 发布 Plan |
| [`prepare_visit_processed_write_intent.py`](../../../apps/task003/prepare_visit_processed_write_intent.py) | 历史发布写入意图；自身不授权写入 |
| [`prepare_visit_writer_bundle_inventory.py`](../../../apps/task003/prepare_visit_writer_bundle_inventory.py) | 历史 Visit Runtime Bundle 的源文件清单 |
| [`resolve_approved_encounter_raw.py`](../../../apps/task003/resolve_approved_encounter_raw.py) | 历史批准的 Encounter Raw 读取与证据解析 |
| [`resolve_encounter_raw_resume.py`](../../../apps/task003/resolve_encounter_raw_resume.py) | 历史中断 Encounter Raw 发布恢复校验 |
| [`verify_encounter_remote_metadata.py`](../../../apps/task003/verify_encounter_remote_metadata.py) | 历史远端 Encounter Manifest / DQ 元数据只读检查 |
| [`verify_visit_processed_plan.py`](../../../apps/task003/verify_visit_processed_plan.py) | 历史 Visit Processed Plan 与固定证据的比较 |

## 关联入口

[Discovery DAG](../../../airflow/dags/landing_batch_discovery.py) · [Discovery Tests](../../../tests/landing_discovery/) · [Claim Tests](../../../tests/landing_claim/) · [NEW_ONLY READY Policy](../../../contracts/synthea/new-only/ready-publication-policy-v1.json)

这里的历史 `task003` 文件负责 S3 Raw/Processed 发布安全、Intent、Reservation 与 DQ 证据，而不是已经独立实现的新增业务 ETL。Discover 不等于自动 Claim 或 COMMIT。

## 源码维护约定

**新增、删除、重命名或移动本组件负责的 `apps/` 源文件时，必须在同一个 PR 更新此 CODE.md。** CODE.md 只做导航，不能当作重新执行历史脚本的授权。历史 `taskNNN` 程序仍可能被 Docker COPY、Import 或冻结 Contract 引用；先看 [Legacy 重构计划](../LEGACY-CODE-REFACTOR-PLAN.md)。

