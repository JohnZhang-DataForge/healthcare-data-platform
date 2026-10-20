# Local Data Platform 迁移后真实 NEW_ONLY E2E 验收（2026-10-20）

状态：**FULL FRESH-BATCH BUSINESS E2E PASS；遗留清理仍 OPEN**。

## 固定源码与真实运行证据

- Healthcare 运行源码：`569cc7e07ba37e82561b110527e613546a63ee4a`（运行前已核实是 Main；之后 Fabric 文档单独推进，不更改本批 DAG）。
- Self-Runner 实验 Workflow：`.github/workflows/local-dp-fresh-newonly-omop-e2e.yml`，执行分支 `feature/local-dp-fresh-synthea-e2e-20261020`。
- **全链路最终 SUCCESS**：[Self-Runner Run #39422787433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422787433)；首次 DAG `local-dp-fresh-newonly-39422787433`、重复 DAG `local-dp-fresh-skip-39422787433` 都为 `success`。
- 新 Batch 生成与 READY **SUCCESS**：[Run #39421910846](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39421910846)。
- Helm 配置生效 **SUCCESS**：[Run #39422344924](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422344924)，现有 `dw-airflow` / `airflow@1.22.0`，升级时 `--reuse-values --atomic --wait`，没有重新创建 Release 或基础设施。
- 迁移路径：`/opt/airflow/dags/repo/local-data-platform/airflow/dags`（Scheduler、DAG Processor 真实生效）。DAG ID `new_only_omop_consumer`、14 Task、Schedule=None 均保持。
- Helm 可重放配置：`local-data-platform/kubernetes/helm/airflow-postmove-values.yaml`，Airflow 组件 CODE Map 已同步。

## 新数据和 Manifest

- Batch ID：`synthea-new-only-gh-39421910846`；Request ID：`gh-39421910846`。
- Person：**16**；Encounter / Visit：**4,259**；CSV：**18/18**。
- Manifest URI：`s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-20/batch_id=synthea-new-only-gh-39421910846/manifest.json`。
- Manifest SHA256：`01cd1cad227c3d840c899520396ff5dc88b1a3c001a804298ba4920ddd26cac9`。
- 生成 → S3 发布 `PUBLISHED_NEW` → 独立 18/18 S3 Readback → 同请求 `REUSE_EXISTING` 均 PASS；历史 S3 / PG Person/Visit Source ID 冲突为零。

## Airflow → Spark → Fenced Writer

完整 DagRun 的以下 Task 均由真实 Airflow 元数据库核实为 `success`：

`scan_ready_manifests` → `select_verified_new_only_batch` → `inspect_claim_readonly` → `route_new_only_status` → `spark_patient` + `spark_encounter` → `spark_reconcile` → `prepare_writer_handoff` → `route_writer_authorization` → `execute_new_only_writer` → `writer_committed_verified`。

生产者/消费者使用源代码中已有的唯一新批次 Manifest、Claim/Fencing、Handoff、Secret 授权和原子 Writer；**没有绕过原子提交**。相关镜像从运行时源代码冻结 Digest 引用：

| 用途 | 镜像 Digest（运行 DAG / Workflow 声明） |
| --- | --- |
| Synthea NEW_ONLY Generator | `healthcare-synthea-new-only@sha256:36b69a26f25f9b627da693fc1aa70b8d0a37de0af755bcb7d95d140568efa909` |
| Landing Discovery | `healthcare-landing-discovery@sha256:059d94e4d1348c194956203fea6b19be23ec39595127eea397419e66fa4e5924` |
| NEW_ONLY Spark Processing V2 | `healthcare-landing-processing-v2@sha256:9af63252823bae0187b2517a013c147e2df8dfbe9a7c783ac31cd5dd7dbbb937` |
| CDM Claim Reader | `healthcare-data-platform-task004-cdm-runtime@sha256:94979587aeee2f2ea13e2c27ffc5a8850b97381f3f126c72201fe2b2b3086f5e` |
| Atomic Writer | `healthcare-data-platform-new-only-omop-writer@sha256:1565a4481669520916a336e7ce5de52f3856333c43632078d03854b22bc28ae4` |

以上为**源码指定的不可变 Digest**；未将其谎称为重新构建并推送的新镜像或额外独立采集的所有 Pod `imageID`。

## PostgreSQL 独立事务只读验收

[最终 E2E Run #39422787433](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39422787433) 通过独立 `psql` READ ONLY 比较（非依赖 Writer 返回值）：

| 指标 | 之前 | 第一次 COMMIT 后 |
| --- | ---: | ---: |
| `cdm.person` | 208 | 224 |
| `cdm.visit_occurrence` | 21,934 | 26,193 |
| 此 Batch Landing Claim | 0 | 1 |
| 此 Batch `COMPLETED` Claim（含 SHA / attempt=1 / null lease / reconciliation） | 0 | 1 |
| 此 Batch Writer Ledger | 0 | 1 |
| 此 Batch Person Stage | 0 | 16 |
| 此 Batch Visit Stage | 0 | 4,259 |
| 此 Batch VERIFED Commit Checkpoints | 0 | 2 |
| 实际映射并联结到 `cdm.person` 的 Person | 0 | 16 |
| 实际映射并联结到 `cdm.visit_occurrence` 的 Visit | 0 | 4,259 |

由结果确认数据库净增 **16 Person / 4,259 Visit**；Batch 对账 100% 匹配。

## 同一 Batch 真实重放保护

第二次触发相同 Batch/Manifest（`spark_processing=true`、`writer_commit=true` 仍保留）：

- 第二个 DagRun `local-dp-fresh-skip-39422787433`：**success**。
- `already_completed_no_replay`：**success**，Spark、Handoff、Writer Task：**skipped**。
- 第二次独立 PostgreSQL Readback 与第一次 Readback 执行 `diff -u`：**零差异**。
- 标记：`NEW_ONLY_SAME_BATCH_REPEAT_SKIP=PASS`、`NEW_ONLY_REPEAT_ZERO_PG_CHANGE=PASS`、`LOCAL_DP_FRESH_NEW_ONLY_REAL_E2E=PASS`。

## 仍然开放

本证据只证明迁移后新 Batch 业务 E2E、Writer 和同 Batch 幂等性。4.1/4.8–4.10 的历史源码/测试清理及其他非业务系统（Fabric/FHIR/HL7）未因此被视为完成；OpenSpec Change 在这些任务完成前保持 **Active**。旧历史完成 Batch 的探针 [Run #39419382836](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/39419382836) 失败、被 Airflow 在路径修复后标记 failed，没有被错误记为 PASS，也没有被覆盖写入。

