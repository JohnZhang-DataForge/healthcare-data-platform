---
status: active
scope: spark-source-code-map
last_verified: 2026-10-24
source_sha: d019429332e794e412426cf9c5053bafa043c05e
---

# Spark — CODE / 源码导航

> **Spark 组件唯一权威源码地图**。覆盖当前 Git 树中全部非文档 Spark 文件，直接导航 PySpark、数据 Contract、SparkApplication 模板和相关测试。基于上方 Source SHA 静态核对，不代表本次做过集群 Live 验证；理解组件设计读 [README.md](README.md)，运行前遵守 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。

## 1. Person Canonical / OMOP Transformation

| 源文件（直接链接） | 职责 / 使用边界 |
| --- | --- |
| [`load_omop_person_stage.py`](../../../../local-data-platform/spark/apps/person/load_omop_person_stage.py) | OMOP Person Stage 数据形态和 ID 检查及加载入口；区别于最终事务 Writer |
| [`map_canonical_patient_to_omop.py`](../../../../local-data-platform/spark/apps/person/map_canonical_patient_to_omop.py) | Canonical Patient → OMOP Person 映射、Concept 与主键检查 |
| [`publish_canonical_patient.py`](../../../../local-data-platform/spark/apps/person/publish_canonical_patient.py) | Canonical Patient 合同校验和已批准 Raw 发布 |
| [`synthea_patient_adapter.py`](../../../../local-data-platform/spark/apps/person/synthea_patient_adapter.py) | Synthea Patient CSV → Canonical Patient Spark Adapter |

## 2. Visit Canonical / Candidate / Processed

| 源文件（直接链接） | 职责 / 使用边界 |
| --- | --- |
| [`map_encounter_to_visit_candidate.py`](../../../../local-data-platform/spark/apps/visit/map_encounter_to_visit_candidate.py) | 纯 DataFrame Encounter→Visit Candidate 映射，无提交副作用 |
| [`processed_visit_writer_core.py`](../../../../local-data-platform/spark/apps/visit/processed_visit_writer_core.py) | Visit Processed 受 Permit/Reservation 保护的 write-once Parquet 核心 |
| [`publish_processed_dq.py`](../../../../local-data-platform/spark/apps/visit/publish_processed_dq.py) | Visit Processed DQ 证据的不可变发布和读回 |
| [`publish_processed_manifest.py`](../../../../local-data-platform/spark/apps/visit/publish_processed_manifest.py) | Visit Processed APPROVED Manifest 最终发布 Gate |
| [`run_visit_processed_writer.py`](../../../../local-data-platform/spark/apps/visit/run_visit_processed_writer.py) | 历史 Visit Processed Spark Driver；受外部锁和 Permit Gate 约束 |
| [`synthea_encounter_adapter.py`](../../../../local-data-platform/spark/apps/visit/synthea_encounter_adapter.py) | Synthea Encounter CSV → Canonical Encounter Adapter |
| [`validate_encounter_raw_for_visit.py`](../../../../local-data-platform/spark/apps/visit/validate_encounter_raw_for_visit.py) | Encounter Raw/Person Mapping 的只读前置检查 |
| [`validate_persisted_visit_candidate.py`](../../../../local-data-platform/spark/apps/visit/validate_persisted_visit_candidate.py) | 已存储 Visit Candidate Parquet 的独立校验 |
| [`validate_visit_candidate_preflight.py`](../../../../local-data-platform/spark/apps/visit/validate_visit_candidate_preflight.py) | Visit Candidate schema/键/血缘 Preflight，禁止在此写库 |

## 3. 公共函数、发布与 Reconciliation

| 源文件（直接链接） | 职责 / 使用边界 |
| --- | --- |
| [`publish_canonical_entity.py`](../../../../local-data-platform/spark/apps/publish_canonical_entity.py) | 多种 Canonical 实体共用的 Raw 校验/不可变发布 |
| [`reconcile_person_visit.py`](../../../../local-data-platform/spark/apps/task004/reconcile_person_visit.py) | 历史 TASK004 Person/Visit 同批数据只读 Reconciliation |
| [`batch_manifest.py`](../../../../local-data-platform/spark/common/batch_manifest.py) | Landing Manifest、Batch Identity、S3 URI 共用解析/验证 |
| [`canonical_gate.py`](../../../../local-data-platform/spark/common/canonical_gate.py) | Canonical Schema/Metadata/Unique Key 共用 Gate |
| [`omop.py`](../../../../local-data-platform/spark/common/omop.py) | OMOP 人口学 Concept 和 Schema/Person 辅助校验 |

## 4. Canonical、OMOP Mapping Contracts

| 源文件（直接链接） | 职责 / 使用边界 |
| --- | --- |
| [`encounter-v1.json`](../../../../local-data-platform/spark/contracts/canonical/encounter-v1.json) | 版本化数据 Contract：encounter v1（字段/身份/映射协议；不是可执行代码） |
| [`patient-v1.json`](../../../../local-data-platform/spark/contracts/canonical/patient-v1.json) | 版本化数据 Contract：patient v1（字段/身份/映射协议；不是可执行代码） |
| [`person-v5.4.json`](../../../../local-data-platform/spark/contracts/omop/person-v5.4.json) | 版本化数据 Contract：person v5.4（字段/身份/映射协议；不是可执行代码） |
| [`visit-candidate-v1.json`](../../../../local-data-platform/spark/contracts/omop/visit-candidate-v1.json) | 版本化数据 Contract：visit candidate v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-class-v1.json`](../../../../local-data-platform/spark/contracts/omop/visit-class-v1.json) | 版本化数据 Contract：visit class v1（字段/身份/映射协议；不是可执行代码） |

## 5. Processed Visit、ID Map、Writer Safety Contracts

| 源文件（直接链接） | 职责 / 使用边界 |
| --- | --- |
| [`visit-business-key-snapshot-v1.json`](../../../../local-data-platform/spark/contracts/processed/visit-business-key-snapshot-v1.json) | 版本化数据 Contract：visit business key snapshot v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-candidate-publication-v1.json`](../../../../local-data-platform/spark/contracts/processed/visit-candidate-publication-v1.json) | 版本化数据 Contract：visit candidate publication v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-cdm-materialization-preflight-v1.json`](../../../../local-data-platform/spark/contracts/processed/visit-cdm-materialization-preflight-v1.json) | 版本化数据 Contract：visit cdm materialization preflight v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-cdm-materialization-result-v1.json`](../../../../local-data-platform/spark/contracts/processed/visit-cdm-materialization-result-v1.json) | 版本化数据 Contract：visit cdm materialization result v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-id-allocation-recovery-amendment-v1.json`](../../../../local-data-platform/spark/contracts/processed/visit-id-allocation-recovery-amendment-v1.json) | 版本化数据 Contract：visit id allocation recovery amendment v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-id-allocation-result-v1.json`](../../../../local-data-platform/spark/contracts/processed/visit-id-allocation-result-v1.json) | 版本化数据 Contract：visit id allocation result v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-id-mutation-contract-v1.json`](../../../../local-data-platform/spark/contracts/processed/visit-id-mutation-contract-v1.json) | 版本化数据 Contract：visit id mutation contract v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-id-readonly-preflight-v1.json`](../../../../local-data-platform/spark/contracts/processed/visit-id-readonly-preflight-v1.json) | 版本化数据 Contract：visit id readonly preflight v1（字段/身份/映射协议；不是可执行代码） |
| [`visit-writer-safety-v1.json`](../../../../local-data-platform/spark/contracts/processed/visit-writer-safety-v1.json) | 版本化数据 Contract：visit writer safety v1（字段/身份/映射协议；不是可执行代码） |

## 6. SparkApplication 模板（*.yaml.tpl）

| 源文件（直接链接） | 职责 / 使用边界 |
| --- | --- |
| [`canonical-raw-publish.yaml.tpl`](../../../../local-data-platform/spark/manifests/common/canonical-raw-publish.yaml.tpl) | SparkApplication 参数模板：canonical raw publish（需渲染参数与审批，不能直接 Apply） |
| [`person-canonical-adapter.yaml.tpl`](../../../../local-data-platform/spark/manifests/task002/person-canonical-adapter.yaml.tpl) | SparkApplication 参数模板：person canonical adapter（P4 Person Canonical Adapter：仅 NEW_ONLY v2 子镜像覆盖，增加 per-job OpenLineage Listener 1.47.1 / Marquez private HTTP；保留原主程序和所有业务参数，不能直接 Apply） |
| [`person-canonical-raw-publish.yaml.tpl`](../../../../local-data-platform/spark/manifests/task002/person-canonical-raw-publish.yaml.tpl) | SparkApplication 参数模板：person canonical raw publish（需渲染参数与审批，不能直接 Apply） |
| [`person-omop-map.yaml.tpl`](../../../../local-data-platform/spark/manifests/task002/person-omop-map.yaml.tpl) | SparkApplication 参数模板：person omop map（需渲染参数与审批，不能直接 Apply） |
| [`person-stage-load.yaml.tpl`](../../../../local-data-platform/spark/manifests/task002/person-stage-load.yaml.tpl) | SparkApplication 参数模板：person stage load（需渲染参数与审批，不能直接 Apply） |
| [`encounter-canonical-adapter.yaml.tpl`](../../../../local-data-platform/spark/manifests/task003/encounter-canonical-adapter.yaml.tpl) | SparkApplication 参数模板：encounter canonical adapter（P4 Visit Encounter Canonical Adapter：仅 NEW_ONLY v2 子镜像覆盖，增加 per-job OpenLineage Listener 1.47.1 / Marquez private HTTP；保留原主程序和所有业务参数，不能直接 Apply） |
| [`visit-candidate-preflight.yaml.tpl`](../../../../local-data-platform/spark/manifests/task003/visit-candidate-preflight.yaml.tpl) | SparkApplication 参数模板：visit candidate preflight（需渲染参数与审批，不能直接 Apply） |
| [`visit-processed-prefix-reader.yaml.tpl`](../../../../local-data-platform/spark/manifests/task003/visit-processed-prefix-reader.yaml.tpl) | SparkApplication 参数模板：visit processed prefix reader（需渲染参数与审批，不能直接 Apply） |
| [`visit-processed-writer.yaml.tpl`](../../../../local-data-platform/spark/manifests/task003/visit-processed-writer.yaml.tpl) | SparkApplication 参数模板：visit processed writer（需渲染参数与审批，不能直接 Apply） |
| [`visit-raw-metadata-reader.yaml.tpl`](../../../../local-data-platform/spark/manifests/task003/visit-raw-metadata-reader.yaml.tpl) | SparkApplication 参数模板：visit raw metadata reader（需渲染参数与审批，不能直接 Apply） |
| [`visit-raw-preflight.yaml.tpl`](../../../../local-data-platform/spark/manifests/task003/visit-raw-preflight.yaml.tpl) | SparkApplication 参数模板：visit raw preflight（需渲染参数与审批，不能直接 Apply） |
| [`person-visit-reconciliation.yaml.tpl`](../../../../local-data-platform/spark/manifests/task004/person-visit-reconciliation.yaml.tpl) | SparkApplication 参数模板：person visit reconciliation（P4 同批 Person/Visit 只读 Reconcile：仅 NEW_ONLY v2 子镜像覆盖，增加 per-job OpenLineage Listener 1.47.1 / Marquez private HTTP；保留原主程序和所有业务参数，不能直接 Apply） |

### NEW_ONLY OpenLineage 父 Run 上下文（仅新 V2 子镜像）

- [`openlineage_parent_context.py`](../../../../local-data-platform/spark/common/openlineage_parent_context.py)：通用渲染后、K8s Apply 前的 Spark 配置注入器，只接受真实 Airflow Provider 宏提供的 `namespace + job + UUID`；未 opt-in 的旧调用保持原样，不发事件、不查询或修改 Marquez/S3/PG。
- [`test_openlineage_parent_context.py`](../../../../local-data-platform/tests/spark/test_openlineage_parent_context.py)：独立离线正向/负向验证，含错 Namespace、Job、UUID、错误 appName、部分上下文及旧调用兼容。
- 既有 `05d/05e/05f` Shell 在原渲染后、`kubectl apply --dry-run` 前调用；由单个 `landing-processing-v2` 子镜像覆盖三脚本及注入器。**源码改动不表示镜像已发布**；Writer/Claim/Fencing 和 Spark 业务算法不变。

## 7. 相关测试与集成

- **Person / Canonical**：[Canonical Gate Unit Tests](../../../../local-data-platform/tests/task002/test_canonical_gate_static.py)、[Person Mapper Static Tests](../../../../local-data-platform/tests/task002/test_person_omop_mapper_static.py)、[Canonical Publisher Tests](../../../../local-data-platform/tests/task003/test_generic_canonical_publisher.py)。
- **Visit / Processed**：[Visit Candidate Preflight](../../../../local-data-platform/tests/task003/test_visit_candidate_preflight_static.py)、[Processed Writer Core](../../../../local-data-platform/tests/task003/test_processed_visit_writer_core.py)、[Processed Writer Driver](../../../../local-data-platform/tests/task003/test_visit_processed_driver.py)、[Persisted Candidate Validator](../../../../local-data-platform/tests/task003/test_persisted_visit_candidate_validator.py)。
- **Reconciliation / orchestration**：[Reconciliation Tests](../../../../local-data-platform/tests/task004/test_person_visit_reconciliation_source.py)、[NEW_ONLY Spark Integration](../../../../local-data-platform/tests/landing_discovery/test_new_only_v2_spark_processing.py)、[Airflow CODE](../airflow/CODE.md)。
- **下游持久化**：[OMOP CODE](../omop/CODE.md)；SparkApplication `COMPLETED`、Canonical/Processed Parquet 和 Writer Handoff 不代表 PostgreSQL 事务 COMMIT。
- **观测**：[Portal / Marquez](../../platform-portal/README.md) 的独立 Spark OpenLineage Smoke 不等于 Person/Visit 真实业务血缘已闭环。
- **历史已验收事实**：[TASK004 Final E2E](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/49936b51d4beadc69383e931efc3e72d2f0db47e/docs/tasks/TASK-004-NEW-ONLY-E2E-FINAL-ACCEPTANCE-2026-10-14.zh-CN.md)。

## 历史 Shell / 脚本导航（由 spark 组件负责）

> 本清单是历史 Step Shell 的**代码索引，不是按顺序执行的 Runbook**。这些文件可能使用固定 Git SHA/Batch ID、操作 S3/PG/K8s、修改仓库源码或生成本地报告；任何执行须先读脚本全文并核对 [Safe Operations](../../../engineering/operations/SAFE-OPERATIONS.md)。新脚本必须按组件/能力命名，不能新增 `taskNNN` 路径。

## 历史 task002（6 个入口）

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`00-reset-task002.sh`](../../../../local-data-platform/scripts/task002/00-reset-task002.sh) | [HIGH / review] 历史 TASK002 reset 历史 Task 脚本；可能清理本地文件/临时资源，禁止无审查重放 |
| [`01-inspect-person-baseline.sh`](../../../../local-data-platform/scripts/task002/01-inspect-person-baseline.sh) | [CHECK / verify effects] 历史 TASK002 inspect person baseline 脚本；可能仍产生报告/Pod，不能仅凭文件名判断副作用 |
| [`02-capture-legacy-person-blueprint.sh`](../../../../local-data-platform/scripts/task002/02-capture-legacy-person-blueprint.sh) | [PREPARE / may write] 历史 TASK002 capture legacy person blueprint 脚本 |
| [`03-run-person-canonical-adapter.sh`](../../../../local-data-platform/scripts/task002/03-run-person-canonical-adapter.sh) | [EXECUTE / review] 历史 TASK002 run person canonical adapter 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`04-publish-canonical-patient.sh`](../../../../local-data-platform/scripts/task002/04-publish-canonical-patient.sh) | [EXECUTE / review] 历史 TASK002 publish canonical patient 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`05-map-person-omop.sh`](../../../../local-data-platform/scripts/task002/05-map-person-omop.sh) | [EXECUTE / review] 历史 TASK002 map person OMOP 脚本 |

> **历史源码安装器退役（2026-10-20，Task 4.9 第六批）**：移除 2 份已物化到正式 Git 源码的历史安装器；对应正式源码、Contract、运行脚本、单测 **4/4 全字节 MATCH** 且全部保留。原生成器可使用固定 Git 恢复地址：[`05g2c2b-prepare-visit-processed-writer-core.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/e3ce9f2e5adbfd22f25e3bfca1b2ae892f4f086a/local-data-platform/scripts/task003/05g2c2b-prepare-visit-processed-writer-core.sh)、[`05g2c2c1-prepare-visit-processed-spark-driver.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/e3ce9f2e5adbfd22f25e3bfca1b2ae892f4f086a/local-data-platform/scripts/task003/05g2c2c1-prepare-visit-processed-spark-driver.sh)。不可将历史链接当作现行入口，也不自动重放旧 Batch。

> **2026-10-20 OpenSpec Task 4.9 集中清理**：一次性退役本组件 3 个仅用于安装/生成现有正式源码的历史 TASK003 Shell。基于 Main `db4242dcbc752a021456240e98210ba595161510`，两仓 818 个源码/配置文件扫描、19/19 生成产物完整字节匹配；正式执行器、测试、Contracts 和 Writer/Fencing/恢复脚本一律保留。全项目 26 个初始候选中另外 17 个因动态输出、实际消费引用、运维或测试职责保持 HOLD。历史源码固定恢复链接：[`05f-prepare-visit-candidate-mapping.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/db4242dcbc752a021456240e98210ba595161510/local-data-platform/scripts/task003/05f-prepare-visit-candidate-mapping.sh)、[`05f2a-prepare-visit-candidate-driver.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/db4242dcbc752a021456240e98210ba595161510/local-data-platform/scripts/task003/05f2a-prepare-visit-candidate-driver.sh)、[`05g2c2c3d2b1-prepare-persisted-validator-source.sh`](https://github.com/JohnZhang-DataForge/healthcare-data-platform/blob/db4242dcbc752a021456240e98210ba595161510/local-data-platform/scripts/task003/05g2c2c3d2b1-prepare-persisted-validator-source.sh)。详情见 [集中清理证据](../../../../openspec/changes/relocate-local-data-platform/evidence/LOCAL-DP-TASK003-CONSOLIDATED-RETIREMENT-20261020.md)；本 CODE Map 更改不等于候选版本真实 E2E PASS。

## 历史 task003（6 个入口）

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`03-run-encounter-canonical-adapter.sh`](../../../../local-data-platform/scripts/task003/03-run-encounter-canonical-adapter.sh) | [EXECUTE / review] 历史 TASK003 run encounter canonical adapter 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`04-prepare-canonical-encounter-publish.sh`](../../../../local-data-platform/scripts/task003/04-prepare-canonical-encounter-publish.sh) | [PREPARE / may write] 历史 TASK003 prepare canonical encounter publish 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`04-publish-canonical-encounter.sh`](../../../../local-data-platform/scripts/task003/04-publish-canonical-encounter.sh) | [EXECUTE / review] 历史 TASK003 publish canonical encounter 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`04-resume-canonical-encounter-publish.sh`](../../../../local-data-platform/scripts/task003/04-resume-canonical-encounter-publish.sh) | [LEGACY / review] 历史 TASK003 resume canonical encounter publish 脚本 |
| [`05f2b-prepare-visit-candidate-runtime.sh`](../../../../local-data-platform/scripts/task003/05f2b-prepare-visit-candidate-runtime.sh) | [PREPARE / may write] 历史 TASK003 prepare visit candidate runtime 脚本；可能生成/覆盖仓库源码或报告，先检查目标路径 |
| [`05f2c-validate-visit-candidate.sh`](../../../../local-data-platform/scripts/task003/05f2c-validate-visit-candidate.sh) | [CHECK / verify effects] 历史 TASK003 validate visit candidate 脚本 |

## 历史 task004（3 个入口）

| 真实源文件 | 主要职责与执行风险 |
| --- | --- |
| [`05d-run-person-canonical.sh`](../../../../local-data-platform/scripts/task004/05d-run-person-canonical.sh) | [EXECUTE / review] 历史 TASK004 run person canonical 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`05e-run-visit-canonical.sh`](../../../../local-data-platform/scripts/task004/05e-run-visit-canonical.sh) | [EXECUTE / review] 历史 TASK004 run visit canonical 脚本；可能创建 Job/ConfigMap 或写入 S3/PG，需授权 |
| [`05f-reconcile-person-visit.sh`](../../../../local-data-platform/scripts/task004/05f-reconcile-person-visit.sh) | [CHECK / verify effects] 历史 TASK004 reconcile person visit 脚本 |

## 8. 源码与文档维护规则

**在 `spark/` 下新增、删除、移动或重命名任意源码、JSON Contract、YAML 模板，或变更本组件负责的 `scripts/` Shell 时，必须在同一个 PR 修改本 `CODE.md`。** 入口、职责、关键接口或依赖变化也必须审查导航内容。普通内部重构未影响导航时不要求无意义地更改文件。

[CODE Map CI](../../../../.github/quality/scripts/check_component_code_map.py) 除 Airflow / Apps 外，对 Spark 的源码清单完整性、缺失/失效/重复链接及同 PR 同步作静态校验。当前收录 **44 个文件：18 Python、14 JSON、12 YAML 模板**；以后以 Git Tree 为准，不把这个统计当永久常量。

历史 `task002`、`task003`、`task004` 模板/代码/合同仍可能用于兼容，不能因导航整理而修改、重新运行或批量 Rename。所有 `*.yaml.tpl` 必须先检查镜像 Digest、Namespace、ServiceAccount、S3 Batch Prefix 和共享 Spark 资源并发；新源码按 [组件命名规范](../../../engineering/development/CODE-ORGANIZATION-AND-NAMING.md) 管理。

> **P4 版本边界**：三个源模板 Git 中已加 Listener，但基础 `task004-runtime` 的旧 GHCR 镜像不会因为源码修改自动变化。本轮仅在 `landing-processing-runtime` 子镜像 Dockerfile 显式覆盖三个模板，供 `new_only_omop_consumer` 的 `spark_patient` / `spark_encounter` / `spark_reconcile` 使用。后续需对该一个镜像执行手动 Clean Build/Smoke/`publish-latest` 并真实验证，未完成前不得宣称正在运行的 Pod 已带 Listener。
