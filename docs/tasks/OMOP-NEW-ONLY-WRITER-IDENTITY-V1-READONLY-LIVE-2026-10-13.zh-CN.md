# OMOP NEW_ONLY Writer Identity v1 — 真实只读验收

> 2026-10-13 EDT / 2026-10-14 UTC。Healthcare PR #109 / Self-Runner PR #92。真实 Self-Hosted Runner [Run 38500077292](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38500077292) SUCCESS。TASK004 IN PROGRESS，TASK005 ON HOLD。不是 Spark/Writer 新批 COMMIT、也不是实际 Writer 正向 ROLLBACK。

## 实现

- 保持旧 task004-airflow-* Plan ID、无显式版本的原 Legacy Plan SHA、所有 Existing Target Drift 机制不变。
- 新前缀 synthea-new-only-* **必须显式声明** writer_identity_version=synthea-new-only-v1；绑定 manifest SHA/URI、Person/Visit processing URI、ingest_date、source_version、Person 1..100 和 Visit 1..100000。版本也绑定 immutable plan_sha256。
- 版本信息从 Plan Builder 传播至 Adapter、Precommit Gate、SQL renderer 和 cdm_runtime_cli。协议文件 contracts/omop-writer/writer-batch-identity-v1.json。
- NEW_ONLY 对 allow_commit=True 一律拒绝，抛出 new_only_commit_requires_fenced_writer；ROLLBACK-only 仍允许；历史旧 Writer 显式 opt-in 不变。
- 不兼容 UPDATE_ONLY 和 MIX_DATA，不变更现有 S3 READY 数据、PVC、Claim 或 PostgreSQL；新 Writer 镜像尚未发布或部署。

## 真实验收

首次 [Run 38499991748](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38499991748)：测试 Fixture 忘记 source_version，19/20 PASS，PG 步骤跳过；不涉及生产代码逻辑错误或 DB DML。第二次 Run 38500077292：按 Healthcare SHA 4d92dd1ee657cb8b24bdc90f46990637334d43d5 精确 checkout，20 OMOP Writer + 31 Dynamic + 2 S3 Writer 共 **53/53 tests PASS**。原有 Existing Target Drift SQL 仍存在，NEW_ONLY 禁止 COMMIT PASS。

真实 worker03 PG BEGIN TRANSACTION READ ONLY 独立读回：Person 136、Visit 9391、Claim Ledger 0。v2 Batch synthea-new-only-gh-38497355290 对应 Claim/Legacy Batch Ledger/Stage/Commit 均为 0；Readback Before/After diff 为空；POSTGRESQL_MUTATION=NO、S3_READY_MUTATION=NO、CLAIM_ENABLE=NO。

## 下一步与约束

1. 对已存在的 1 Person/812 Encounter v2 READY Batch 实际运行 NEW_ONLY **手工 Processing-only** Spark：Manifest SHA dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80，验证 Airflow XCom、Person/Visit Parquet 与 S3 readback。仍禁止 Claim 与 PG DML，不修改原不可变 READY。
2. 从真 Spark 输出构建显式 NEW_ONLY Plan，使用经新 digest 构建的 Writer runtime 做 real S3 read + 无碰撞 precommit + Existing Target Drift 负例/正例。
3. **设计 Person→Visit 同一 PostgreSQL 事务最终 ROLLBACK**。旧 renderer 每个 entity 自己 BEGIN/ROLLBACK，Visit 需要 Person VERIFIED；两个单实体独立 ROLLBACK 不可能证明完整的全批正例，不能假称完成。验证全部 OMOP/ID Map/Legacy Ledger/Stage/Commit/Claim 前后不变。
4. 在真正 COMMIT 之前加入事务内 Claim token + lease fencing、Manifest/source key 复核、失败恢复/未知结果查账/并发、DB reconciliation 与 COMPLETED/同批 replay。
5. 再启用受控 Airflow 新批 Claim→Spark→Writer 和处理 25-item Discovery preview 上限；通用 NEW_ONLY Request Workflow v1/v2 image selector 是独立尾项。UPDATE_ONLY/MIX_DATA/TASK005 保持 ON HOLD。

**本轮不代表真实新批 ROLLBACK 或任何 COMMIT。**