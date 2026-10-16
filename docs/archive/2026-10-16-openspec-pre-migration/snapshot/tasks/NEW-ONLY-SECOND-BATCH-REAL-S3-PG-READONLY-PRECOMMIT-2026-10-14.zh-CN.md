# TASK004 NEW_ONLY 第二个真实 Batch：Airflow Spark→真 S3 Parquet→PG Read-only Precommit

> **2026-10-14 EDT — SUCCESS / NO BUSINESS COMMIT.** [Self-Runner Run 38565372429](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38565372429) 全流程 SUCCESS（OMOP Writer 47/47 + Landing Discovery 48/48 regressions）。本轮从**真实已经执行成功的 Airflow DagRun** `newonly-spark-handoff-38563933551` 取回 `prepare_writer_handoff` 的不可变 XCom，S3 GET 当前真实 Processing Parquet，解码 **70 Person / 11,487 Visit**，使用实际 `cdm_reader` PostgreSQL `READ ONLY` 事务核对源键与 Manifest、Claim、既有 Writer/Stage/Checkpoint，完全 PASS。无 Spark 重跑、无业务 DML/COMMIT、无 Airflow Auto Claim。

## 关键数据来源

- 原始 S3 READY Batch：`synthea-new-only-gh-38489944582`，Manifest SHA `be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256`。
- Spark Processing 和真实 Writer Handoff：已完成的 [Airflow 实时 Runner 38563933551](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38563933551) SUCCESS；Patient **70**、Encounter **11487**，Processing S3 两实体 Handoff Plan SHA/Manifest SHA/URI、Writer identity version `synthea-new-only-v1`。
- 本轮**没有触发新的 DagRun 或 Spark**；从 Airflow metadata 的 DagRun、TaskInstance state=success 与实际 `prepare_writer_handoff` XCom，读取完整 Plan JSON 作为当前测试唯一输入。
- 在 worker02 使用固定 `task004-cdm-runtime@sha256:94979587aeee2f2ea13e2c27ffc5a8850b97381f3f126c72201fe2b2b3086f5e` 和 `cdm_reader` 登录真实 OMOP DB，只读连接，源码从候选 Healthcare commit SHA pin 的 ConfigMap 注入。临时 Job/ConfigMaps 跑完清理。

## 真正完成的检查

```text
SECOND_READY_READER_REGRESSIONS=PASS
SECOND_READY_OMOP_BEFORE=PASS
SECOND_READY_REAL_AIRFLOW_XCOM_READBACK=PASS
SECOND_REAL_S3_PERSON_ROWS=70
SECOND_REAL_S3_VISIT_ROWS=11487
SECOND_NEW_ONLY_PG_READER_SOURCE_COLLISIONS=0
SECOND_NEW_ONLY_IMMUTABLE_HANDOFF=PASS
SECOND_NEW_ONLY_REAL_S3_PG_READONLY_PREFLIGHT=PASS
REAL_SECOND_NEW_ONLY_END_TO_END_READER_PREFLIGHT=PASS
SECOND_NEW_ONLY_OMOP_BEFORE_AFTER_UNCHANGED=PASS
SPARK_RERUN=NO
BUSINESS_COMMIT=NO
```

**实际只读审计**：S3 Manifest 原始字节由既有 Source adapter 重新 GET 校验 SHA，两个 Processing 前缀各只有预期 Parquet，所有 Person/Visit row fingerprint/去重/父键经 `precommit_gate` 验证，通过 `etl.person_id_map`、`etl.visit_occurrence_id_map` 查询得到 **0 overlap**；新 Batch Claim `ABSENT`、Legacy Writer Ledger 0、Stage 0、Checkpoint 0。禁止以这次结果自动授权真正业务 COMMIT，实际负载与版本仍需入库时重检。

| PostgreSQL 实际前后 | Before | After |
|---|---:|---:|
| `cdm.person` | 137 | 137 |
| `cdm.visit_occurrence` | 10203 | 10203 |
| `etl.person_id_map` | 137 | 137 |
| `etl.visit_occurrence_id_map` | 10203 | 10203 |
| 新 Batch Claim | 0 | 0 |
| 新 Batch Writer Stage | 0 | 0 |
| 新 Batch Verified Commit Checkpoints | 0 | 0 |
| 旧批次 Claim=COMPLETED | 1 | 1 |

## 版本化代码与下一步

- `apps/omop_writer/audit_second_new_only_ready.py`：只读、固定本真实 Batch 的验证 adapter，拒绝旧已 COMMIT Batch、Manifest SHA/Count 漂移、不正确的 `cdm_reader` 权限、任何 Source ID overlap/Claim/Writer 历史。仅输出有限元数据；不会执行 SQL Writer 或隐式 COMMIT。
- `tests/omop_writer/test_second_new_only_real_preflight.py`：坏批次、错 SHA、错行数、旧批次、伪造 Handoff、非法 PG Principal、Claim/Source ID 漂移和脚本静态不写检查。
- Self-Runner `.github/workflows/task004-second-newonly-real-pg-reader.yml` SHA-pin Healthcare candidate、查实际 Airflow Handoff、一次 worker02 只读 Pod、前后 DB readback diff；不用生产自动 Claim。
- **NEXT：** 针对**完全相同的真实 S3 70/11487 已处理 Parquet**，执行有上限的单事务 Fencing+联合 Person/Visit SQL **ROLLBACK-only**（允许 PG sequence nextval 有所前进，但没有行持久化），而后独立 PG Reconciliation/readback。**经过真实 ROLLBACK PASS 并得到针对这个新 Batch 的业务 COMMIT 授权，才可以进入持久 COMMIT**；目前仍不可在现有 Airflow DAG 直接执行 Writer。
- 双 Writer 并发和复杂 Lease 恢复仍为 FUTURE ENHANCEMENT；不要阻塞 Demo 主线。TASK004 IN PROGRESS / TASK005 ON HOLD。

之前 [PR #130](https://github.com/JohnZhang-DataForge/healthcare-data-platform/pull/130) 已完成真正 Airflow 新批 Spark Person/Visit→Handoff 并在 [Run 38563933551](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38563933551) 成功，**禁止重复开发/重跑 Spark**；本轮填补的是下一段真正 S3→Postgres 读回与预提交检查。
