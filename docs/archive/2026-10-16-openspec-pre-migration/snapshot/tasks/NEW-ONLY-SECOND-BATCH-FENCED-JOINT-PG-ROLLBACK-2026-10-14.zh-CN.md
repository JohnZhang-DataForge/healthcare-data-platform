# TASK004 第二个真实 NEW_ONLY Batch — Person70 / Visit11487 同事务 Fencing 联合 PostgreSQL ROLLBACK

> **2026-10-14 EDT — LIVE PASS / 无业务 COMMIT。** [Self-Runner 38566745511](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38566745511) **SUCCESS**：真正已完成 Airflow Spark `newonly-spark-handoff-38563933551` 的不可变 XCom → 真 S3 70 Patient/11487 Encounter Processing Parquet → `cdm_reader` PG READ ONLY SOURCE-ID preflight 0 collisions → 完整动态原子 Claim+Fencing+CDM Person+Visit+实际数据库全行 Reconciliation SQL → **将唯一业务 COMMIT 强制替换成显式 ROLLBACK** → 独立 PG Before/After 一致。99 个单测通过（Writer 51/51，Landing 48/48）。TASK004 IN PROGRESS、TASK005 ON HOLD。

## 真实运行与明确范围

- Batch：`synthea-new-only-gh-38489944582`，Manifest SHA `be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256`。原始 S3 READY 与 Spark Processing **已经存在，不重跑 Spark/不再生成 Synthea**。
- Airflow 源 DagRun：[Run 38563933551](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38563933551) 已成功产出两实体 S3 Parquet 和 `NEW_ONLY_WRITER_HANDOFF_VERIFIED_NOT_AUTHORIZED`。本轮从真实 Airflow metadata XCom 获取该不可变 handoff，不制造模拟输入。
- 审计使用 `cdm_reader` 真实只读 PostgreSQL `omop` 登录，校验每个 Person/Visit Source ID 未在映射表重用、Manifest/Plan SHA/Parquet fingerprint/Person parent 关系及未入库 Claim/Writer Ledger；再次读取 S3。
- 真实 SQL 由 `apps/omop_writer/dynamic_new_only_commit.py` 复用原首次 1/812 成功原子 Writer。为演练 `apps/omop_writer/generate_second_new_only_fenced_rollback.py` 检验仅一个 `BEGIN;`、仅一个 `COMMIT;` 原始边界、三次 `assert_active_claim`、完整 `DO $reconcile$` / `DO $complete$`，然后**删掉后置 COMMIT 查询，将唯一 `COMMIT;` 替换成 `ROLLBACK;`**。先执行真正角色切换与 Owner/Attempt/Manifest/Lease Fencing，再完整 Person→Visit 插入、对账和 Claim COMPLETED（仅本事务内部），全部 ROLLBACK；绝无持久 Claim。
- Runner 通过 `kubectl exec -i` 使用真实 `omop_admin` Session 执行该渲染的 **ROLLBACK-only** SQL。由于 PostgreSQL 序列 `nextval()` 非事务性，Sequence 值**可能前进**；不能说数据库所有内部状态没有变化。实际持久化表业务行绝不应增加。
- SQL/Claim Owner 只在临时 Pod 与 Self-Runner 临时工作目录，不上传 workflow artifacts，不作为泛用任意 SQL COMMIT 执行器。仍保持 Airflow `schedule=None`、`CLAIM_ENABLE=NO`，不启用自动业务写。

## 正式运行日志标记

```text
Writer regressions: 51/51
Landing regressions: 48/48
SECOND_REAL_S3_PERSON_ROWS=70 (既有只读验收)
SECOND_REAL_S3_VISIT_ROWS=11487 (既有只读验收)
SECOND_NEW_ONLY_WRITER_SQL_REAL_PERSON=70
SECOND_NEW_ONLY_WRITER_SQL_REAL_VISIT=11487
SECOND_NEW_ONLY_WRITER_SQL_ROLLBACK_ONLY=PASS
SECOND_NEW_ONLY_WRITER_NO_BUSINESS_COMMIT=PASS
SECOND_REAL_NEW_ONLY_FENCED_SQL_ROLLBACK_SAFE=PASS
SECOND_NEW_ONLY_REAL_S3_TO_PG_JOINT_FENCED_ROLLBACK=PASS
SECOND_NEW_ONLY_FENCED_PG_BEFORE_AFTER_UNCHANGED=PASS
SPARK_RERUN=NO
BUSINESS_COMMIT=NO
```

| PostgreSQL 持久表 | Before | After |
|---|---:|---:|
| `cdm.person` | 137 | 137 |
| `cdm.visit_occurrence` | 10203 | 10203 |
| `etl.person_id_map` | 137 | 137 |
| `etl.visit_occurrence_id_map` | 10203 | 10203 |
| 本批 `etl.landing_batch_ledger` Claim | 0 | 0 |
| 本批 Writer Stage | 0 | 0 |
| 本批 Writer Checkpoints | 0 | 0 |
| 首个旧 batch Claim `COMPLETED` | 1 | 1 |

全轮真实 PostgreSQL `diff -u` 前后通过。**本批还没有真实 PostgreSQL 业务 COMMIT**。

## 现在的 Demo 主线剩余事项

1. **下一个明确步骤：首次持久 COMMIT 本第二 Batch 70 Person / 11487 Visit。** 必须获得用户针对这份新 batch 的明确业务写入授权。COMMIT 时必须在实际数据库重新检查 Claim ABSENT、0 Existing Target Drift、当前 S3 SHA 与 Plan 不漂移；复用已验收的动态单事务完整 Body 和对账，写入后独立 PG Readback、`COMPLETED`，不可把 `ROLLBACK` 的成功当成已经 COMMIT。
2. **Airflow 自动编排尾端尚未接通：** 当前 `new_only_omop_consumer` 已真正执行 Spark Person/Visit/Handoff 并停在 `writer_awaits_live_preflight`。首次新的 COMMIT 成功后，应把版本化/审核的 Writer KPO/Executor 接入这个 DAG，适度验证失败重试/已完成批次跳过，再验收新 Batch 的端到端自动 COMMIT。
3. 单批次串行，双 Writer 并发/未知提交复杂恢复为 FUTURE ENHANCEMENT，不阻塞 Demo；坚持 source key、Manifest、同事务 Fencing/两实体 full-row Reconciliation。TASK005 ON HOLD。
4. 多会话协作：若涉及再次修改/运行共用 Airflow/Spark，先确认其他 Session 无冲突；本轮没有重新执行 Spark。

**本轮只限真 ROLLBACK；下一轮真实业务 COMMIT 的授权需明确。**
