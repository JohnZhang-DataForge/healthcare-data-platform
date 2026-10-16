---
status: active
scope: spark-source-code-map
last_verified: 2026-10-16
source_sha: f16e652ce0018fed5bb5d485f6eebe21c96d6603
---

# Spark — CODE / 源码导航

> **Spark 组件唯一权威源码地图**。覆盖当前 Git 树中全部非文档 Spark 文件，直接导航 PySpark、数据 Contract、SparkApplication 模板和相关测试。基于上方 Source SHA 静态核对，不代表本次做过集群 Live 验证；理解组件设计读 [README.md](README.md)，运行前遵守 [Safe Operations](../../operations/SAFE-OPERATIONS.md)。

## 1. Person Canonical / OMOP Transformation

| 源文件（直接链接） | 职责 / 使用边界 |
| --- | --- |
| [`load_omop_person_stage.py`](../../../spark/apps/person/load_omop_person_stage.py) | OMOP Person Stage 数据形态和 ID 检查及加载入口；区别于最终事务 Writer |
| [`map_canonical_patient_to_omop.py`](../../../spark/apps/person/map_canonical_patient_to_omop.py) | Canonical Patient → OMOP Person 映射、Concept 与主键检查 |
| [`publish_canonical_patient.py`](../../../spark/apps/person/publish_canonical_patient.py) | Canonical Patient 合同校验和已批准 Raw 发布 |
| [`synthea_patient_adapter.py`](../../../spark/apps/person/synthea_patient_adapter.py) | Synthea Patient CSV → Canonical Patient Spark Adapter |

## 2. Visit Canonical / Candidate / Processed

| 源文件（直接链接） | 职责 / 使用边界 |
| --- | --- |
| [`map_encounter_to_visit_candidate.py`](../../../spark/apps/visit/map_encounter_to_visit_candidate.py) | 纯 DataFrame Encounter→Visit Candidate 映射，无提交副作用 |
| [`processed_visit_writer_core.py`](../../../spark/apps/visit/processed_visit_writer_core.py) | Visit Processed 受 Permit/Reservation 保护的 write-once Parquet 核心 |
| [`publish_processed_dq.py`](../../../spark/apps/visit/publish_processed_dq.py) | Visit Processed DQ 证据的不可变发布和读回 |
| [`publish_processed_manifest.py`](../../../spark/apps/visit/publish_processed_manifest.py) | Visit Processed APPROVED Manifest 最终发布 Gate |
| [`run_visit_processed_writer.py`](../../../spark/apps/visit/run_visit_processed_writer.py) | 历史 Visit Processed Spark Driver；受外部锁和 Permit Gate 约束 |
| [`synthea_encounter_adapter.py`](../../../spark/apps/visit/synthea_encounter_adapter.py) | Synthea Encounter CSV → Canonical Encounter Adapter |
| [`validate_encounter_raw_for_visit.py`](../../../spark/apps/visit/validate_encounter_raw_for_visit.py) | Encounter Raw/Person Mapping 的只读前置检查 |
| [`validate_persisted_visit_candidate.py`](../../../spark/apps/visit/validate_persisted_visit_candidate.py) | 已存储 Visit Candidate Parquet 的独立校验 |
| [`validate_visit_candidate_preflight.py`](../../../spark/apps/visit/validate_visit_candidate_preflight.py) | Visit Candidate schema/键/血缘 Preflight，禁止在此写库 |

## 3. 公共函数、发布与 Reconciliation

| 源文件（直接链接） | 职责 / 使用边界 |
| --- | --- |
| [`publish_canonical_entity.py`](../../../spark/apps/publish_canonical_entity.py) | 多种 Canonical 实体共用的 Raw 校验/不可变发布 |
| [`reconcile_person_visit.py`](../../../spark/apps/task004/reconcile_person_visit.py) | 历史 TASK004 Person/Visit 同批数据只读 Reconciliation |
| [`batch_manifest.py`](../../../spark/common/batch_manifest.py) | Landing Manifest、Batch Identity、S3 URI 共用解析/验证 |
| [`canonical_gate.py`](../../../spark/common/canonical_gate.py) | Canonical Schema/Metadata/Unique Key 共用 Gate |
| [`omop.py`](../../../spark/common/omop.py) | OMOP 人口学 Concept 和 Schema/Person 辅助校验 |

## 4. Canonical、OMOP Mapping Contracts

| 源文件（直接链接） | 职责 / 使用边界 |
| --- | --- |
| [`encounter-v1.json`](../../../spark/contracts/canonical/encounter-v1.json) | 版本化数据 Contract：encounter v1（字段/身份/映射协议；不是可执行代码） |
| [`patient-v1.json`](../../../spark/contracts/canonical/patient-v1.json) | 版本化数据 Contract：patient v1（字段/身份/映射协议；不是可执行代码） |
| [`person-v5.4.json`](../../../spark/contracts/omop/person-v5.4.json) | 版本化数据 Contract：person v5.4（字段/身份/映射协议；不是可执行代码） |
| [`visit-candidate-v1.json`](../../../spark/contracts/omop/visit-candidate-v1.json) | 版本化数据 Contract：visit candidate v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-class-v1.json`](../../../spark/contracts/omop/visit-class-v1.json) | 版本化数据 Contract：visit class v1（字段/身份/映射协议；不是可执行代码） |

## 5. Processed Visit、ID Map、Writer Safety Contracts

| 源文件（直接链接） | 职责 / 使用边界 |
| --- | --- |
| [`visit-business-key-snapshot-v1.json`](../../../spark/contracts/processed/visit-business-key-snapshot-v1.json) | 版本化数据 Contract：visit business key snapshot v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-candidate-publication-v1.json`](../../../spark/contracts/processed/visit-candidate-publication-v1.json) | 版本化数据 Contract：visit candidate publication v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-cdm-materialization-preflight-v1.json`](../../../spark/contracts/processed/visit-cdm-materialization-preflight-v1.json) | 版本化数据 Contract：visit cdm materialization preflight v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-cdm-materialization-result-v1.json`](../../../spark/contracts/processed/visit-cdm-materialization-result-v1.json) | 版本化数据 Contract：visit cdm materialization result v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-id-allocation-recovery-amendment-v1.json`](../../../spark/contracts/processed/visit-id-allocation-recovery-amendment-v1.json) | 版本化数据 Contract：visit id allocation recovery amendment v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-id-allocation-result-v1.json`](../../../spark/contracts/processed/visit-id-allocation-result-v1.json) | 版本化数据 Contract：visit id allocation result v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-id-mutation-contract-v1.json`](../../../spark/contracts/processed/visit-id-mutation-contract-v1.json) | 版本化数据 Contract：visit id mutation contract v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-id-readonly-preflight-v1.json`](../../../spark/contracts/processed/visit-id-readonly-preflight-v1.json) | 版本化数据 Contract：visit id readonly preflight v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-writer-safety-v1.json`](../../../spark/contracts/processed/visit-writer-safety-v1.json) | 版本化数据 Contract：visit writer safety v1（字段/身份/映射协议；不是可执行代码） |

## 6. SparkApplication 模板（*.yaml.tpl）

| 源文件（直接链接） | 职责 / 使用边界 |
| --- | --- |
| [`canonical-raw-publish.yaml.tpl`](../../../spark/manifests/common/canonical-raw-publish.yaml.tpl) | SparkApplication 参数模板：canonical raw publish（需渲染参数与审批，不能直接 Apply） |
| [`person-canonical-adapter.yaml.tpl`](../../../spark/manifests/task002/person-canonical-adapter.yaml.tpl) | SparkApplication 参数模板：person canonical adapter（需渲染参数与审批，不能直接 Apply） |
| [`person-canonical-raw-publish.yaml.tpl`](../../../spark/manifests/task002/person-canonical-raw-publish.yaml.tpl) | SparkApplication 参数模板：person canonical raw publish（需渲染参数与审批，不能直接 Apply） |
| [`person-omop-map.yaml.tpl`](../../../spark/manifests/task002/person-omop-map.yaml.tpl) | SparkApplication 参数模板：person omop map（需渲染参数与审批，不能直接 Apply） |
| [`person-stage-load.yaml.tpl`](../../../spark/manifests/task002/person-stage-load.yaml.tpl) | SparkApplication 参数模板：person stage load（需渲染参数与审批，不能直接 Apply） |
| [`encounter-canonical-adapter.yaml.tpl`](../../../spark/manifests/task003/encounter-canonical-adapter.yaml.tpl) | SparkApplication 参数模板：encounter canonical adapter（需渲染参数与审批，不能直接 Apply） |
| [`visit-candidate-preflight.yaml.tpl`](../../../spark/manifests/task003/visit-candidate-preflight.yaml.tpl) | SparkApplication 参数模板：visit candidate preflight（需渲染参数与审批，不能直接 Apply） |
| [`visit-processed-prefix-reader.yaml.tpl`](../../../spark/manifests/task003/visit-processed-prefix-reader.yaml.tpl) | SparkApplication 参数模板：visit processed prefix reader（需渲染参数与审批，不能直接 Apply） |
| [`visit-processed-writer.yaml.tpl`](../../../spark/manifests/task003/visit-processed-writer.yaml.tpl) | SparkApplication 参数模板：visit processed writer（需渲染参数与审批，不能直接 Apply） |
| [`visit-raw-metadata-reader.yaml.tpl`](../../../spark/manifests/task003/visit-raw-metadata-reader.yaml.tpl) | SparkApplication 参数模板：visit raw metadata reader（需渲染参数与审批，不能直接 Apply） |
| [`visit-raw-preflight.yaml.tpl`](../../../spark/manifests/task003/visit-raw-preflight.yaml.tpl) | SparkApplication 参数模板：visit raw preflight（需渲染参数与审批，不能直接 Apply） |
| [`person-visit-reconciliation.yaml.tpl`](../../../spark/manifests/task004/person-visit-reconciliation.yaml.tpl) | SparkApplication 参数模板：person visit reconciliation（需渲染参数与审批，不能直接 Apply） |

## 7. 相关测试与集成

- **Person / Canonical**：[Canonical Gate Unit Tests](../../../tests/task002/test_canonical_gate_static.py)、[Person Mapper Static Tests](../../../tests/task002/test_person_omop_mapper_static.py)、[Canonical Publisher Tests](../../../tests/task003/test_generic_canonical_publisher.py)。
- **Visit / Processed**：[Visit Candidate Preflight](../../../tests/task003/test_visit_candidate_preflight_static.py)、[Processed Writer Core](../../../tests/task003/test_processed_visit_writer_core.py)、[Processed Writer Driver](../../../tests/task003/test_visit_processed_driver.py)、[Persisted Candidate Validator](../../../tests/task003/test_persisted_visit_candidate_validator.py)。
- **Reconciliation / orchestration**：[Reconciliation Tests](../../../tests/task004/test_person_visit_reconciliation_source.py)、[NEW_ONLY Spark Integration](../../../tests/landing_discovery/test_new_only_v2_spark_processing.py)、[Airflow CODE](../airflow/CODE.md)。
- **下游持久化**：[OMOP CODE](../omop/CODE.md)；SparkApplication `COMPLETED`、Canonical/Processed Parquet 和 Writer Handoff 不代表 PostgreSQL 事务 COMMIT。
- **观测**：[Portal / Marquez](../platform-portal/README.md) 的独立 Spark OpenLineage Smoke 不等于 Person/Visit 真实业务血缘已闭环。
- **历史已验收事实**：[TASK004 Final E2E](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)。

## 8. 源码与文档维护规则

**在 `spark/` 下新增、删除、移动或重命名任意源码、JSON Contract 或 YAML 模板，必须在同一个 PR 修改本 `CODE.md`。** 入口、职责、关键接口或依赖变化也必须审查导航内容。普通内部重构未影响导航时不要求无意义地更改文件。

[CODE Map CI](../../../scripts/quality/check_component_code_map.py) 除 Airflow / Apps 外，对 Spark 的源码清单完整性、缺失/失效/重复链接及同 PR 同步作静态校验。当前收录 **44 个文件：18 Python、14 JSON、12 YAML 模板**；以后以 Git Tree 为准，不把这个统计当永久常量。

历史 `task002`、`task003`、`task004` 模板/代码/合同仍可能用于兼容，不能因导航整理而修改、重新运行或批量 Rename。所有 `*.yaml.tpl` 必须先检查镜像 Digest、Namespace、ServiceAccount、S3 Batch Prefix 和共享 Spark 资源并发；新源码按 [组件命名规范](../../development/CODE-ORGANIZATION-AND-NAMING.md) 管理。
