# TASK004 — Synthea Seed / Reference Date 与 Person Source ID 冲突根因排查（2026-10-13）

> **READ-ONLY ROOT-CAUSE AUDIT = PASS；Person Writer 仍因 EXISTING_TARGET_DRIFT BLOCKED。** 本文是上次 [Source ID 只读 Reconciliation Closeout](TASK-004-STEP04F-PERSON-SOURCE-ID-READONLY-RECONCILIATION-CLOSEOUT.md) 的后续，所有新数字来自两个已经存在的真实 S3 Landing Manifest、patients.csv、2026-10-13 新批次 Processing Parquet、PostgreSQL `cdm_reader` SELECT。**没有触发任何新 Synthea、Airflow DAG 或 Writer COMMIT。**

## 一、实际测试与可信来源

- Self-Runner 新审计文件：`task004/smoke/read_only_seed_identity_drift.py`、`.github/workflows/task004-seed-identity-readonly.yml`。
- **最终真实 PASS**：[Self-Runner Actions Run 38447127571](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38447127571)；测试的准确 Self-Runner branch HEAD = `9c0d6e538f43364845876e404cdf72fd42fbee92`；日志包含 `TASK004_SEED_IDENTITY_READONLY_AUDIT=PASS`、`DATABASE_MUTATION=NO`。
- 已合并测试源代码：[Self-Runner PR #70](https://github.com/JohnZhang-DataForge/Self-Runner/pull/70)，squash merge/main = `f3f1a65fd9e30bd549ce352fb429031627827404`。成功的集群运行绑定合并前准确 feature SHA；合并后没有单独的 Main 集群重测（工作流只监控指定 feature push）。
- 额外的出生日期偏移统计在 Run `38447048269` 曾因审计脚本 `date` 变量遮蔽 Python 类而 FAILURE；修复并新提交后 `38447127571` SUCCESS。更早简化测试 `38446909471` 也曾 SUCCESS；不能混淆源码 bug 和业务 drift。
- 本轮只读 Job 在 `dw-spark/worker02` 使用 digest-pinned CDM runtime 与 `task004-cdm-reader-db` 用户，严格 `transaction_read_only=on`，仅读取 S3 和 PG，打印列名和汇总计数，不打印任何患者标识/姓名/日期值。

## 二、两个已存在的生成批次

| 字段 | 2026-10-12 历史批次 | 2026-10-13 新批次 |
|---|---|---|
| Batch ID | `task004-airflow-task004-step03e-38324111846` | `task004-airflow-task004-step03e-38431103586` |
| Population Size | 20 | 20 |
| 实际 `patients.csv` 行数 | **23** | **23** |
| `seed` | **20261012** | **20261012** |
| `clinician_seed` | **20261012** | **20261012** |
| `reference_date` | **20261012** | **20261013** |
| 其余 `source_parameters` | 相同 | 相同 |
| 原始 patients.csv SHA256 | `53d6f94569c67a60ce4d46d83e7ad0a009dc8dbcf60b384da84339008ada0832` | `b64aceade6c2c8bdcb9b2abcf1dabfe2c182b757504bf09fdbf7e3ba5e96430d` |
| Verified Manifest SHA256 | `ecc7cf3b75240e530f2cc96635b25e4eaf0794403e1b04d50d2248cd3aaa5cb1` | `e6dc34dd45357a43561f5e44da4368647440a78363f43b1a762bc8a` |

代码链路复核：
1. `airflow/dags/task004_processing_pipeline.py` 的默认 `seed` 和 `clinician_seed` **都是常量字符串 `20261012`**；每次 `generate_publish` 传入 `REFERENCE_DATE = dag_run.run_after.strftime('%Y%m%d')`、`LANDING_INGEST_DATE = dag_run.run_after.strftime('%Y-%m-%d')`。
2. `images/synthea/entrypoint.sh` 将这些参数转换为 Synthea CLI `-s` / `-cs` / `-r` / `-p`，真实 Manifest `source_parameters` 保留上述输入；两批参数对比证实只有 reference_date 改变。
3. Synthea 使用 reference date 参与出生日期/年龄等生成结果。两次 Seed 相同，生成的 patient ID 完全一致，但内容不一致；此结论由下节真实 S3 数据佐证，不再只是猜测。

## 三、原始 CSV 与 OMOP 字段级统计（不包含患者值）

**两个 23 条 CSV 的 `Id` 集合完全相同**：重合 23、仅历史 0、仅新批次 0；相同完整 CSV 行 0、发生变化完整 CSV 行 23。

两批 `patients.csv` 按 `Id` 一对一比较，下面为**发生变化的患者数**（不是变动的列数）：

| patients.csv 字段 | 变化患者数 |
|---|---:|
| **BIRTHDATE** | **23** |
| DEATHDATE | 3 |
| DRIVERS | 1 |
| HEALTHCARE_COVERAGE | 3 |
| HEALTHCARE_EXPENSES | 4 |
| LAST | 1 |
| MAIDEN | 1 |
| MARITAL | 2 |
| PREFIX | 1 |

**最重要的增量证据：23/23 人的 BIRTHDATE 均准确向后移动 1 天**（`CSV_BIRTHDATE_DELTA_DAYS_1=23`）。这不是数据库写入转换的误差：两份发布在 S3 的原始 `patients.csv` 本身就不同，并通过相应 Manifest SHA256 验证。

从新 CSV 的 23 个 Id 到新批次 Processing 的 23 个 Person source key，集合完全一致（`FRESH_CSV_TO_PROCESSING_IDENTITY=PASS`）。

通过真实 PG 只读比较，23/23 mapping 均指向已经存在的 `cdm.person`，0 identical、23 different；OMOP Person 目标字段差异**只发生在**：

| cdm.person 字段 | 变化 Person |
|---|---:|
| **birth_datetime** | **23** |
| **day_of_birth** | **23** |

其余 Person 字段的已存记录与当前动态适配器拟插入的 payload 均一致。在 PostgreSQL Writer 的 JSONB 完整记录比较标准下，任何一个字段变化都会导致 `BLOCKED:EXISTING_TARGET_DRIFT`；所以这次全部 23 人被拒绝是符合保护契约的结果。

## 四、排查结论：属于生成身份和参考时间策略冲突，而不是数据库插入重复

本次已经独立定位到一个明确、可复现的配置因果链：

```text
DAG default seed / clinician_seed = 20261012（两批相同）
+ REFERENCE_DATE = dag_run.run_after（每天不同）
  ↓
Synthea 生成两个不同批次（两个都为 23 patients）
  ↓
同一批 23 个 synthetic Patient Id 再次出现
  ↓
所有 23 个 birth date 向后移动 1 天
  ↓
OMOP 已映射 source_person_id 重用既有 person_id
  ↓
现有 cdm.person 的 birth_datetime/day_of_birth 与拟写入不一致
  ↓
EXISTING_TARGET_DRIFT fail-closed
```

Synthea 这次不是新生成 23 个独立身份的人，而是**同一组随机身份在不同 reference_date 下重新生成的 23 条合成患者记录**。这也解释为何新一批 Person/Visit Processing 成功，但 PostgreSQL 不能简单追加为新的 Person。

已由上一轮数据库残留审计证实：新批次 `etl.task004_batch_ledger` / `stage` / `commit` 均为 0，CDM Person=136、Visit=9391。本轮再次保证 `DATABASE_MUTATION=NO`；没有把 23 变为 46 或静默更新。

## 五、下一步设计约束（本轮未实施）

若业务含义是**每次新 Airflow 批次生成一组全新患者**，必须保证不同批次有稳定、不同的生成身份输入：优先设计**从 immutable batch identity 派生确定性 Seed**（同 batch/manifest 重放 Seed 不变、跨批次不同），并将 `reference_date` 作为 batch 级冻结输入写入 Manifest，禁止旧 batch 的重放随当天日期漂移。只有测试确认新旧 Source ID 不重合后，才能再进入单独授权的真实 S3→Person Writer ROLLBACK。

若业务含义是**同一批患者的日期进展/后续新事件**，则不能当作独立新患者强行 INSERT；应设计显式版本管理、修正策略和 OMOP update/审计语义，并明确真实 DOB 是否允许变化。对于本次结果，生日集体向后一天不应被默认为合法的患者更新。

**任何方案都不允许绕过 EXISTING_TARGET_DRIFT、覆盖 23 条既有 Person、把 run_id 当成业务自然键或在未知旧批次的状态下自动 COMMIT。** 本轮不触发任何新的 Synthea、Writer ROLLBACK/COMMIT、完整 Airflow DB 写入或 TASK005。

**Final Status：ROOT-CAUSE READONLY AUDIT = PASS；TASK004 OMOP CDM LOOP = IN PROGRESS / WRITER BLOCKED；TASK005 Condition = ON HOLD。**
