# OMOP Dynamic Writer — NEW_ONLY Pre-COMMIT Safety Gate（2026-10-13）

> **真实 PostgreSQL 只读安全门槛已 PASS，实际 COMMIT 功能仍 NOT IMPLEMENTED/NOT ENABLED。** 本轮以业务语义命名 `omop_writer`，独立构建并验证新批 Person / Visit 完整 payload、不可变计划指纹、Source ID 撞车、历史批次状态和 Claim 状态。**真实验证所用正例为人工构造的测试计划/测试行，不是新 Synthea 发布的 S3 Batch；不能将正例结果视为真实新源已可入库。** 不连接 Airflow Writer，也不修改 `cdm.person` 或 `cdm.visit_occurrence`。

## 1. 代码交付与权限边界

- `apps/omop_writer/precommit_gate.py`：`validate_input` 及 `inspect_new_only`。严格接受已形成的 `task004_cdm_materialization_plan.plan` 与已经经 `task004_cdm_dynamic_adapters` 转换的 Person/Visit prepared rows；重新计算每行 `row_fingerprint`，验证人、Visit 数量、Visit 对本批 Person 的 parent key，强制 NEW_ONLY 实际 Person 1～100、Visit 1～100000，输出 **`commit_authorized=False`**。
- 只允许 PostgreSQL `cdm_reader` 身份、`transaction_read_only=on`，拒绝它拥有 `cdm.person INSERT`。SELECT 检查 `etl.task004_batch_ledger` 历史批次、`etl.person_id_map` 已映射患者源 ID、`etl.visit_occurrence_id_map` 已映射就诊源 ID、`etl.landing_batch_ledger` 的 Manifest 身份和 Lease 状态。NEW_ONLY 存在任意既有 Person/Visit Source Key 冲突时 **`BLOCKED:NEW_ONLY_SOURCE_KEY_COLLISION`**；历史 Batch 拒绝；有异质 Manifest SHA/URI 拒绝。
- 默认 `require_claim=False` **仅用于只读预审**：对于未见过的新 Source ID，输出 `READY_TO_CLAIM`，并明确这**不是实际批次授权，也没有锁定任何 Source Key**。严格 `require_claim=True` 要求现存 `PROCESSING` 且未过期、Manifest SHA/URI 匹配，返回 `READY_TO_LOAD_CHECK`，仍然 **`commit_authorized=False`**。真实 COMMIT 必须在同一个受控事务中检验 lease owner/token、manifest/identity/source、真正对账与 checkpoint，不能只凭本次查询提前放行。
- `apps/omop_writer/verify_real_postgres_readonly.py`：通过受限账号在真正 `dw-postgre/omop` 运行构造测试正例与由数据库内部抽取、**不输出到日志**的既有 Person 源身份负例；还验证已登记旧 Batch、无 Claim 时 strict gate 拒绝。
- `tests/omop_writer/test_precommit_gate.py`：9 个独立单元测试，覆盖源计划漂移、行指纹/Parent、Person/Visit Key 撞车、Claim 过期、读取账号权限、历史批次及无 DML 的 SQL。
- 实际持久化的**权限最小变更**：`GRANT SELECT ON etl.landing_batch_ledger TO cdm_reader`。仍 **没有 INSERT 权限**，没有 `cdm.person` INSERT 权限。未变更已存在 `cdm_writer` 的写权限；没有建立新 Writer Secret，也没有把 COMMIT 按钮加到 Airflow。

## 2. 真实验收（唯一实际 Self-Runner 测试循环）

- **[Self-Runner Run 38478501009](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38478501009) SUCCESS**：准确 Healthcare feature SHA `4fa51b34b9c6ba643db3dc53a71e0d87c13b6236`，Self-Runner feature workflow SHA `fea5c2439151b2cc38a11d907a15e476bc7c1512`。9 个测试 PASS，真正在 worker02 `dw-spark` 临时受限 Pod 中使用固定旧 CDM Runtime image、`task004-cdm-reader-db` Secret 执行只读 PostgreSQL 审查、清理临时 Job/ConfigMap。
- 关键日志：
  ```text
  OMOP_PRECOMMIT_UNIT_TESTS=PASS
  READER_NEW_CLAIM_SELECT=true
  READER_NEW_CLAIM_INSERT=false
  READER_CDM_PERSON_INSERT=false
  REAL_PG_FRESH_SOURCE_PREFLIGHT=PASS
  REAL_PG_EXISTING_PERSON_SOURCE_BLOCKED=PASS
  REAL_PG_UNCLAIMED_COMMIT_BLOCKED=PASS
  REAL_PG_HISTORICAL_BATCH_BLOCKED=PASS
  REAL_PG_READONLY_PRECOMMIT=PASS
  OMOP_WRITER_PRECOMMIT_REAL_DATABASE=PASS
  OMOP_WRITER_PRECOMMIT_NO_BUSINESS_MUTATION=PASS
  ```
- PostgreSQL 独立 Admin readback（操作前→后）：`cdm.person=136→136`、`cdm.visit_occurrence=9391→9391`、`etl.landing_batch_ledger=0→0`。**无 OMOP 数据 INSERT/UPDATE/DELETE、无实际 Claim**；新给 Reader 的 SELECT GRANT 属于持久权限调整，已如实记录。
- 本轮没有构建或发布新的 `omop_writer` 正式 runtime image；测试只通过 ConfigMap 把 Python 模块载入固定 CDM Runtime（沿用已安装的 `psycopg` 和既有计划/Adapter 代码）。

## 3. 下一完整开发闭环（第三层下一阶段）

1. 把**真实新批** `manifest_uri`、Manifest bytes/SHA、S3 Processing Person/Visit Parquet 和新 XCom row counts 一并固定，确保在 Writer 阶段重新下载并核对；人工构造的测试计划必须**永远不可作为正式 COMMIT 授权**。目前唯一历史测试批已入库，另一批与 23 个患者源 ID 重合（出生日期漂移），因此**不能**强行提交现有历史数据。未来 NEW_ONLY Generator 独立发布真正无冲突批次才有完整正向 COMMIT 测试输入。
2. 在不开放生产 COMMIT 前，建立受控、专用、digest-pinned 的 OMOP Writer Runtime，先完成**真实 S3 Parquet → 实际 PG Writer ROLLBACK**；负例必须验证既有历史 Person/Visit Source ID 漂移被挡住。旧 `task004_cdm_dynamic_pg_writer.py` 原来的确可生成 `COMMIT;` SQL，但没有对现有两段事务在未知提交响应时进行 claim-owner fencing、精确 `inserted_rows` 对账和最终 DB Reconciliation，**不可直接打开**。
3. 确保新 Source ID 的数据库防撞门槛在**实际 COMMIT 事务内再次执行**，消除 read-only audit 与写入之间的竞态；必须同一个 immutable `batch_id + manifest_sha256`，核验活跃 Claim 的 lease_owner、锁、失败恢复、同 batch replay 语义。Person 先、Visit 后，并附独立读回的字段/外键/计数/映射和 Ledger COMPLETED/UNKNOWN COMMIT 处理。
4. 上述都通过后，再把受控 Writer 加为 Airflow KPO 并显式分阶段开启；不得改变现有每15分钟只读 Scan + Claim Guard + 默认跳过 Spark 的安全行为。

**状态：OMOP_PRECOMMIT_READONLY=REAL_PG_PASS；OMOP_DYNAMIC_COMMIT=NOT_IMPLEMENTED；AUTO_NEW_BATCH_CLAIM=OFF；TASK004=IN_PROGRESS；TASK005=ON_HOLD。**
