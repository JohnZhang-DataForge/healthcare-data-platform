# TASK004 — Airflow NEW_ONLY 真实第二批 Spark Person/Visit → Writer Handoff LIVE SUCCESS

> **2026-10-14 EDT — REAL LIVE SUCCESS，Spark/Processing/Writer Handoff 阶段完成；还没有 OMOP 入库。** [Self-Runner Run 38563933551](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38563933551) 全 Job **SUCCESS**，Healthcare [PR #130](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/130) 已合并 Main（`f6c4a6e5dfa280fae127f58e20f88e7133e0ed2b`），Self-Runner [PR #104](https://github.com/JohnZhang-DataForge/Self-Runner/pull/104) 已合并 Main（`9c2770944a36224177dbc8190b49baadd34ec5bf`）。真实 Airflow DagRun 已执行 Spark Person **70** / Visit **11,487**，Parquet readback PASS，生成不可变 NEW_ONLY Writer Handoff；PostgreSQL Person/Visit/Claim/Stage/Checkpoint 一行未改。TASK004 IN PROGRESS，TASK005 ON HOLD。

## 一、为什么复用第二个真实 READY，不再生成 Synthea

本轮**仅此 Session** 修改 Spark，用户明确允许实际 Spark 运行。选择已在 S3 READY 发布、尚未 Claim/未写入 OMOP 的现存批次：

```text
batch_id=synthea-new-only-gh-38489944582
manifest_uri=s3://health-landing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38489944582/manifest.json
manifest_sha256=be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256
original_person_rows=70
original_encounter_rows=11487
READY file_count=18
```

该批来自先前独立 Synthea Request `gh-38489944582`，不同于**已经正式 OMOP COMMIT**的 `synthea-new-only-gh-38497355290`（Person 1/Visit 812），不可混为同一批，也禁止重新对已完成批次进行 Spark + Writer COMMIT。

## 二、真实 Main 新增 DAG 逻辑

```text
new_only_omop_consumer — schedule=None / default paused
  scan_ready_manifests (S3 verified READ ONLY)
       ↓
  select_verified_new_only_batch
       ↓
  inspect_claim_readonly (real PG landing_claim_worker)
       ↓
  route_new_only_status
       ├── 已 COMMITTED：already_completed_no_replay
       ├── 新 ABSENT + 无 spark_processing=true：unclaimed_batch_hold
       └── 新 ABSENT + 手工 spark_processing=true
                 ├── spark_patient  (worker02, pinned v2)
                 └── spark_encounter (worker02, pinned v2)
                            ↓
                        spark_reconcile
                            ↓
                        prepare_writer_handoff
                            ↓
                        writer_awaits_live_preflight
                          [安全终点: 不会自动 Claim/COMMIT]
```

- `airflow/dags/new_only_omop_routing.py` 新增手工 `spark_processing=true`，必须同时具备 `consumer_readonly=true`、Batch/URI/SHA 精确匹配真实 S3 Discover，以及 PostgreSQL 当前 `ABSENT`。COMPLETED 即使传了 Spark 标记仍直接跳过；定时/无参数永不执行 Spark。将纯 Claim 状态校验拆成 `classify_new_only_claim()` 以供 Writer Handoff 复核。
- `airflow/dags/landing_spark_processing.py` 原 `make_processing_pod()` factory 保留原历史 `image=PROCESSING_IMAGE_SELECT`；**仅**通过 `image_override=NEW_ONLY_PROCESSING_IMAGE` 显式设置已真实验收的固定 v2 digest。拒绝其他 arbitrary override，历史 Spark DAG 行为不改变。
- `airflow/dags/new_only_omop_consumer.py` 添加两个并行 Spark、Processing reconcile、`prepare_writer_handoff` 和 HOLD。使用现有 worker02 KPO / Kubernetes SparkApplication / SeaweedFS 读写；**没有增加一个 Writer Pod 或 COMMIT 分支**。
- `airflow/dags/new_only_omop_writer_handoff.py` 使用纯 `classify_new_only_claim()` 验证新批 ABSENT，校验两个 Spark XCom、Parquet URI、Source/Batch/ingest_date、Count，生成 SHA 锁定的计划；标识 `NEW_ONLY_WRITER_HANDOFF_VERIFIED_NOT_AUTHORIZED`、`database_mutation_authorized=false`。
- 既有 `landing_batch_discovery` 历史流程没有重新设计/重启；没有触发新的 Synthea Generator。

## 三、Runner 真实证据

```text
# Offline gate — 早期测试对旧镜像 factory 文字合同断言失败后已修复
Run 38563480753: FAIL, no Spark or database mutation
Run 38563629454: SUCCESS, 48 Landing + 42 Writer = 90 regression tests
# 真正 K8s/Airflow live run
Run 38563933551: SUCCESS
NEW_ONLY_SECOND_BATCH_DB_ABSENT=PASS
NEW_ONLY_SPARK_GITSYNC_EXACT_MAIN=PASS
NEW_ONLY_SPARK_REAL_DAGBAG_AND_V2_IMAGE=PASS
NEW_ONLY_SPARK_NO_CLAIM_OR_WRITER_KPO=PASS
NEW_ONLY_SPARK_NO_CONCURRENT_ACTIVE_APPLICATION=PASS
NEW_ONLY_SPARK_TEMPORARY_MANUAL_UNPAUSE=PASS
NEW_ONLY_SPARK_REAL_MANUAL_DAGRUN_SUBMITTED=PASS
NEW_ONLY_SPARK_REAL_DAGRUN_STATE=success
NEW_ONLY_REAL_SPARK_PERSON_ROWS=70
NEW_ONLY_REAL_SPARK_VISIT_ROWS=11487
NEW_ONLY_REAL_SPARK_PARQUET_READBACK=PASS
NEW_ONLY_REAL_SPARK_IMMUTABLE_WRITER_HANDOFF=PASS
NEW_ONLY_REAL_SPARK_NO_BUSINESS_COMMIT=PASS
NEW_ONLY_SPARK_DAG_REPAUSED=PASS
NEW_ONLY_SPARK_OMOP_TABLES_UNCHANGED=PASS
CLAIM_ENABLE=NO
OMOP_BUSINESS_MUTATION=NO
```

真实同一次 Airflow Run 的 TaskInstance 状态：`scan_ready_manifests`、`select_verified_new_only_batch`、`inspect_claim_readonly`、`route_new_only_status`、`spark_patient`、`spark_encounter`、`spark_reconcile`、`prepare_writer_handoff`、`writer_awaits_live_preflight` 全 `success`。两个非本次分支 `already_completed_no_replay` 和 `unclaimed_batch_hold` 均 `skipped`。TaskInstance/XCom 验收在真实 Scheduler 数据库中完成；没有拿静态样本虚构成功。

**实际已写入的 Processing S3 Parquet（需用于后续 Writer，不得手工改造成其他 run_id）：**

Person:
```text
s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38489944582/entity=patient/run_id=task004-person-20261014T122824Z-9/work/normalized/data/
```

Encounter:
```text
s3a://health-processing/source=synthea/source_version=v3.3.0/ingest_date=2026-10-14/batch_id=synthea-new-only-gh-38489944582/entity=encounter/run_id=task004-encounter-20261014T122824Z-9/work/normalized/data/
```

两份 Processing 数据确实由 Spark 新运行生成，**Processing Bucket 有新增 Parquet**；S3 READY/Manifest 字节没有改变。

## 四、PostgreSQL 独立 Before/After（真实 omop）

| 表或状态 | Before | After |
|---|---:|---:|
| `cdm.person` | 137 | 137 |
| `cdm.visit_occurrence` | 10,203 | 10,203 |
| `etl.person_id_map` | 137 | 137 |
| `etl.visit_occurrence_id_map` | 10,203 | 10,203 |
| Claim Ledger 总数 | 1 | 1 |
| **本轮新批** Claim | 0 | 0 |
| 本轮新批 Writer Batch Ledger | 0 | 0 |
| 本轮新批 Stage | 0 | 0 |
| 本轮新批 Commit/Checkpoint | 0 | 0 |
| **前轮旧批** Claim COMPLETED | 1 | 1 |

Self-Runner 在执行结束后用独立 PostgreSQL `BEGIN TRANSACTION READ ONLY` 重新查询并将两份结果 `diff -u` 对比完全一致：**没有 Claim、没有 CDM COMMIT、没有新的 Writer Ledger/Stage/Checkpoint**。验证结束 Airflow DAG 再次 `paused`，无持续自动 Spark 定时调度。

## 五、唯一正确 NEXT：该真实 Spark 新批的受控 Writer 前置审计和事务验证

现已具备真正 READY Batch+Manifest SHA、实际 Processing Person/Visit URI、2 个真实 Spark XCom 及不可变 Plan。下一阶段优先：

1. 从真实 Airflow `prepare_writer_handoff` XCom 或以上固定数据签名提取 `plan_sha256`，在 **worker02** 使用 `cdm_reader` 身份重新读出真实 S3 Parquet、校验 row fingerprint/parent、并重新读 **worker03 PostgreSQL** 的 Source Key 映射碰撞和 Claim 状态，严格保证当前 batch 仍 `ABSENT` / 0 Writer Legacy Ledger；严禁直接 COMMIT。
2. 在不重新执行 Spark 的前提下，调用本阶段已有的 `apps/omop_writer/dynamic_new_only_commit.py` 原子 SQL Renderer，**先做真实 70+11487 Person/Visit 的 bounded ROLLBACK-only test**；只有独立 PG 对账与幂等门槛全部 PASS，才考虑下一轮经明确授权的 COMMIT。
3. 在完成动态 Writer 的真实数据库验证之前，不把 `writer_awaits_live_preflight` 替换成会自动对所有新批 COMMIT 的 KPO。当前 `new_only_omop_consumer` 仍 `schedule=None`/默认 paused/手动 opt-in。
4. 当前用户已明确**只有此 Session 修改 Spark**，本轮无跨 Session 冲突；以后若 Portal/Spark 并行开发恢复，继续遵守 `docs/platform-portal/SESSION-COORDINATION-POLICY.zh-CN.md` 的人工协调。
5. 双 Writer 并发压测、复杂 Lease unknown COMMIT 恢复是 FUTURE ENHANCEMENT，不阻塞 Demo 的**单 Writer 原子性和重放不重复**门槛。

**结论：本次 Spark LIVE + Airflow Handoff 真实成功且数据安全；TASK004 仍 IN PROGRESS，TASK005 ON HOLD，Portal A4 HOLD。**
