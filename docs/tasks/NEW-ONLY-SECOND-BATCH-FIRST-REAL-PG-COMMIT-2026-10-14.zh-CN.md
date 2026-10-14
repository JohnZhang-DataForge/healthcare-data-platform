# TASK004 第二个真实 NEW_ONLY Batch — 首次持久化 COMMIT 与独立 PostgreSQL 对账

> **2026-10-14 EDT — 正式 SUCCESS。** 经过用户明确授权，第二个真实 NEW_ONLY v2 Batch `synthea-new-only-gh-38489944582` 已将 **70 Person + 11,487 Visit** 真正 **COMMIT** 进 PostgreSQL OMOP 数据库，Claim 同事务转为 **COMPLETED**。此前 [ROLLBACK-only 验收](NEW-ONLY-SECOND-BATCH-FENCED-JOINT-PG-ROLLBACK-2026-10-14.zh-CN.md) 的「尚未入库」陈述已成为历史。正式证据：[Self-Runner Run 38575457166](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38575457166) **所有 Job SUCCESS**。**这个批次现在已经入库，任何新 Agent 都不能再用它当作首次 READY Batch 重试/强制提交 Writer。**

## 1. 原始数据与严格执行范围

- Immutable NEW_ONLY Batch：`synthea-new-only-gh-38489944582`。
- Manifest SHA256：`be6806a520d74f5c57886f39086363003a432170c45e71828addedc39b4e1256`。
- 真正的 Airflow Spark 前置执行来自 [Run 38563933551](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38563933551)；实际 `new_only_omop_consumer` 的 `prepare_writer_handoff` XCom 提供已验证的 Person **70** + Visit **11487** S3 Processing URI / Plan SHA。
- 本轮复用现有 Airflow XCom、S3 Parquet、`cdm_reader` 真 PostgreSQL 只读检查；**未重跑 Spark、Synthea、未修改 S3 READY，也没有启用 Airflow 自动 Claim 或真正 Airflow Writer KPO**。
- `apps/omop_writer/commit_second_new_only_once.py` 是专用、严格限定第二批次 Manifest SHA/Person70/Visit11487 的单次 SQL 生成器，且仅在真实源、Handoff 和 PG 状态全部满足时渲染；使用前一次 ROLLBACK-only 已验证的**同一个** `dynamic_new_only_commit.generate_dynamic_commit_sql` 原子 SQL Renderer。
- SQL 在实际 `omop_admin` PostgreSQL 连接中执行、借助 `SET LOCAL ROLE landing_claim_worker/cdm_writer` 限制有效权限；Claim PROCESSING→Fenced Writer Person/Visit→Stage / Mapping / VERIFIED checkpoints→实际 Person/Visit full-row DB Reconciliation→最终 Fencing→Claim COMPLETED→**一次 COMMIT**。不是两独立 PG 角色登录的生产多会话实现。

## 2. 数据库持久化结果：独立新 Session 实测

| PostgreSQL 表/批次 | Before | After | 变化 |
|---|---:|---:|---:|
| `cdm.person` | 137 | **207** | +70 |
| `cdm.visit_occurrence` | 10203 | **21690** | +11487 |
| `etl.person_id_map` | 137 | **207** | +70 |
| `etl.visit_occurrence_id_map` | 10203 | **21690** | +11487 |
| Claim Ledger 总数 | 1 | **2** | +1 |
| 本新批次 Claim | 0 | **1** | +1 |
| 本新批次 Claim `COMPLETED`，Attempt 1，Owner/Lease NULL，proof SHA 非空 | 0 | **1** | +1 |
| 本新批次 Writer Legacy Ledger | 0 | **1** | +1 |
| 本新批次 Stage 总数 | 0 | **11557** | +11557 |
| 新批次 Person Stage | 0 | **70** | +70 |
| 新批次 Visit Stage | 0 | **11487** | +11487 |
| 新批次 VERIFIED Writer Checkpoint | 0 | **2** | +2 |
| 本批源键真正映射到 `cdm.person` | 0 | **70** | +70 |
| 本批源键/父键真正映射到 `cdm.visit_occurrence` | 0 | **11487** | +11487 |
| 首批 `synthea-new-only-gh-38497355290` Claim `COMPLETED` | 1 | **1** | 不变 |

单独的真实 PG `READ ONLY` session 对 `cdm`、两个 ID Maps、Claim、两个 Stage、2 VERIFIED Checkpoints、Source ID/父键 Join 都作了读取并逐项核验；SQL 原始事务内部也执行了两实体实际目标行的完整字段对账。**没有仅凭 Runner SQL 返回值推断持久化成功**。

## 3. 自证的真实 Runner 输出

```text
Self-Runner run 38575457166: SUCCESS
OMOP Writer tests: 55/55 PASS
Landing tests: 48/48 PASS
SECOND_READY_OMOP_BEFORE=PASS
SECOND_READY_REAL_AIRFLOW_XCOM_READBACK=PASS
SECOND_COMMIT_REAL_S3_CDM_READER_PREFLIGHT=PASS
SECOND_COMMIT_REAL_PERSON_ROWS=70
SECOND_COMMIT_REAL_VISIT_ROWS=11487
SECOND_COMMIT_SQL_ONE_TRANSACTION=PASS
SECOND_NEW_ONLY_SINGLE_TX_COMMIT_SQL_SAFETY=PASS
SECOND_NEW_ONLY_FIRST_REAL_BUSINESS_COMMIT=PASS
NEW_COMPLETED=1
NEW_STAGE=11557
NEW_PERSON_STAGE=70
NEW_VISIT_STAGE=11487
NEW_CHECKPOINT=2
PERSON_MAPPED=70
VISIT_MAPPED=11487
SECOND_NEW_ONLY_INDEPENDENT_DURABLE_DB_RECONCILIATION=PASS
SECOND_BATCH_REPLAY_SKIP=1
SECOND_NEW_ONLY_DUPLICATE_CLAIM_SKIPPED=PASS
SECOND_BATCH_NO_SECOND_WRITER_COMMIT=PASS
SPARK_RERUN=NO
S3_READY_MUTATION=NO
AIRFLOW_AUTO_CLAIM=NO
```

## 4. 重复执行约束与失败记录

- 第一次 [Run 38572127827](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38572127827) **FAILED BEFORE COMMIT**：Runner 的两条 `grep` 安全检查命令被截断，Bash 解析失败；独立 PG 检查 137/10203、该新批 Claim0 / Stage0 / Checkpoint0，**没有执行业务 DML/COMMIT**。
- 在用户再次要求重试后，仅修复这两条截断 Bash 断言；第二次 [Run 38575457166](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38575457166) **SUCCESS** 且 PostgreSQL 确认新增数据。这是本新批的唯一业务 COMMIT。
- 后续以实际 `landing_claim_worker` 有效权限执行 `INSERT … ON CONFLICT DO NOTHING`，证实 `SECOND_BATCH_REPLAY_SKIP=1`，已完成 Claim 未被重新创建、没有第二次 Writer COMMIT。该验证**不是**完整 Airflow 业务 Writer 重放演练，不能泛化为端到端多批次自动消费完成。
- 这一专用一次性 GitHub Actions workflow 只作为**历史验收证据**保留；任何 Session 都不得重新运行或再次 push 来触发对此批次的 COMMIT。生成器和运行时 SQL 对已有 Claim/Writer 历史均 fail-closed，但重复触发只会污染运营日志。
- 序列 `nextval()` 可能并非严格连续，本轮以业务实际行数和 Source Key mapping 对账为准。

## 5. 后续主线

1. **正式新批次第一次持久化 Writer COMMIT 已完成**；TASK004 仍 `IN PROGRESS`。
2. **尚未闭环：** `new_only_omop_consumer` 原 DAG 的 `writer_awaits_live_preflight` 仍是 HOLD；首次真实 COMMIT 由用户授权、Runner 人工受控触发，**不是** Airflow 自动调用 Writer KPO。下一步需要实现受控 Writer 执行器/审计状态回报，并针对**另一个尚未入库的全新 NEW_ONLY READY** Batch 验证完整 Airflow 自动入库。不能重用这两个已经 COMMIT 的 Batch 充当未入库测试对象。
3. 可先在 Airflow 中对已入库批次进行只读 `COMPLETED→SKIP` 行为验收、以及安全 Reconciliation/Writer 状态监控，不调用 Spark；再针对新批实现完整生命周期。
4. 双 Writer 并发压测、复杂租约恢复继续 `FUTURE ENHANCEMENT`；Portal A4 HOLD，TASK005 ON HOLD；共享 Spark 再次执行前按多 Session 约定协调。

**当前 PostgreSQL 业务基准：Person 207 / Visit 21690 / Claim Ledger 2（两个实际 NEW_ONLY 批次均 COMPLETED）。**
