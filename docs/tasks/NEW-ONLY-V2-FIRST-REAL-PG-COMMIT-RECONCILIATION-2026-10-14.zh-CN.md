# TASK004 — 首次真实 NEW_ONLY v2 Person+Visit PostgreSQL 业务 COMMIT：Claim、联合 Writer、DB Reconciliation

> **2026-10-14 EDT — 首次真实业务 COMMIT 确认成功。** [Self-Hosted Runner 38555481037](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38555481037) 全步骤 **SUCCESS**。真实已存在、不可变的 NEW_ONLY v2 Batch `synthea-new-only-gh-38497355290` 的 **1 Person + 812 Visit** 经过只读 S3/PG Source ID 审计、最小权限 Claim/Writer 角色、同一 PostgreSQL 事务两实体 SQL + 全量 DB row-by-row reconciliation，正式业务 **COMMIT**。独立读回 Person 136→137、Visit 9391→10203、两个 ID Map 对应增加；新的 Claim Ledger 为 **COMPLETED**，Stage 813、两实体 VERIFIED Checkpoints 2。**这一次与此前所有 ROLLBACK-only 验收不同，真正发生了业务持久化。** TASK004 仍 IN PROGRESS、TASK005 ON HOLD。

## 1. 本次用户授权与严格执行边界

用户明确批准进行**首次业务 COMMIT**；仅固定已经通过真 S3→Spark→PG ROLLBACK 的 Batch：
- `batch_id=synthea-new-only-gh-38497355290`，Synthea v3.3.0，v2 verified READY。
- Immutable Manifest SHA256：`dfb5d30e83c6a9b35b3a723137a5f3ab67649ad94ef1801e2bae3ef42fe5fa80`。
- 不重新触发 Synthea/Spark；**复用**经过独立实时 S3 GET 解码的 Person 1、Visit 812 Processing Parquet。
- 不修改任何历史 S3 READY、Manifest，Airflow `CLAIM_ENABLE=NO` / 自动消费仍关闭，不触碰 Portal A4 或 TASK005。
- 通过 GitHub Connector 分别提交 Healthcare 候选功能分支与 Self-Runner 专用一次性 GitHub Actions；Runner checkout **精确 Healthcare SHA** `a93f9f7c6faccb9c6164263bc07b5ea92faf5f3d`。
- 首次 COMMIT 使用手工授权 **单 Batch / 单 Pod S3 Reader / 单 PG 数据库事务**；不是多批次 Airflow 自动执行器。防止运行历史 Workflow 重复写入。

## 2. 真正执行的事务顺序

```text
cdm_reader / worker02: READ ONLY S3 1/812 + PG Source ID collision audit
     │  verified Plan SHA, source uniqueness, actual historical map collisions = 0
     ▼
omop_admin PostgreSQL session: BEGIN (before all DML)
     │  fail closed: target Claim/Writer Ledger/Stage/Commit must all be 0
     ▼
SET LOCAL ROLE landing_claim_worker
     │  INSERT real Claim PROCESSING + 30min lease / Owner / Attempt 1
     ▼
SET LOCAL ROLE cdm_writer
     │  same-TX SECURITY DEFINER Claim row-lock Fencing
     │  Person Stage + Map + cdm.person + VERIFIED checkpoint
     │  Visit Stage + Map + cdm.visit_occurrence + VERIFIED checkpoint
     │  immutable plan, Existing Target Drift, parent FK, two checkpoints
     │  same-TX row-by-row cdm.person AND cdm.visit_occurrence reconciliation
     │  same-TX final SECURITY DEFINER fencing
     ▼
SET LOCAL ROLE landing_claim_worker
     │  UPDATE Claim PROCESSING → COMPLETED
     │  record bounded source/Plan/Stage-derived reconciliation_sha256
     ▼
RESET ROLE → one explicit PostgreSQL business COMMIT
     ▼
Independent new READ ONLY PG session verifies durable CDM/Maps/Claims/Stages
     ▼
Same Claim SQL repeated with ON CONFLICT DO NOTHING → existing COMPLETED;
     no second Claim row, transaction ROLLBACK
```

**角色边界精度：** 本轮是通过实际 `omop_admin` Session 的 `SET LOCAL ROLE landing_claim_worker/cdm_writer` 验证真实 DB 有效权限，不是两个独立 K8s Pod 分别使用各自的登录 Secret。所有状态在一个物理数据库事务，Claim 是真实且最后持久为 COMPLETED，不是上轮测试用、最终回滚的 synthetic fixture。专门的 `apps/omop_writer/commit_new_only_batch_once.py` 只接受以上 exact Batch/Manifest/1+812，生成 SQL 临时文件，**不**接入 Airflow 自动执行或通用 COMMIT CLI。

## 3. 实际 Runner PASS 证据与持久化数据

真实 [Self-Runner 38555481037](https://github.com/JohnZhang-DataForge/Self-Runner/actions/runs/38555481037) SUCCESS：

```text
Claim regressions: 26/26 PASS
Writer regressions: 37/37 PASS
FIRST_COMMIT_IMMUTABLE_PLAN=PASS
FIRST_COMMIT_PG_BASELINE_CLEAN=PASS
REAL_NEW_ONLY_SOURCE_READONLY_AUDIT=PASS
ONE_TRANSACTION_ATOMIC_CLAIM_WRITER_COMPLETION=PASS
FIRST_REAL_NEW_ONLY_SINGLE_TX_COMMIT_SQL_SAFETY=PASS
TASK004_NEW_ONLY_REAL_FIRST_BUSINESS_COMMIT=PASS
FIRST_REAL_COMMIT_INDEPENDENT_DB_RECONCILIATION=PASS
REPLAY_COMPLETED_SKIP=1
FIRST_COMMIT_DUPLICATE_CLAIM_SAFELY_SKIPPED=PASS
SPARK_RERUN=NO
AIRFLOW_AUTO_CLAIM=NO
S3_READY_MUTATION=NO
```

| PostgreSQL 真实持久表/目标状态 | Before | After |
|---|---:|---:|
| `cdm.person` | 136 | **137** |
| `cdm.visit_occurrence` | 9391 | **10203** |
| `etl.person_id_map` | 136 | **137** |
| `etl.visit_occurrence_id_map` | 9391 | **10203** |
| `etl.landing_batch_ledger` | 0 | **1** |
| NEW_ONLY 真实 Batch Claim | 0 | **1** |
| NEW_ONLY 真实 Batch Claim=COMPLETED 且 proof 非空 | 0 | **1** |
| NEW_ONLY Writer Batch Ledger | 0 | **1** |
| NEW_ONLY Writer Stage 总行数 | 0 | **813** |
| NEW_ONLY Person Stage | 0 | **1** |
| NEW_ONLY Visit Stage | 0 | **812** |
| NEW_ONLY Writer VERIFIED Commit Checkpoints | 0 | **2** |

Reconciliation 是业务事务**提交之前**真实比对 Person/Visit 整行目标 JSONB 与 staged payload/映射键/FK 后通过，且 Commit Checkpoints 两实体 `VERIFIED`/预期 SHA/行数吻合；并非仅用某个上游 digest 随意声称已对账。之后全新连接重新查实际持久行数及 Claim COMPLETED。PG Sequence 分配仍不能假设连续。

## 4. 首次幂等性验证的准确范围

Runner 在提交后，切换为实际 `landing_claim_worker` 权限，重新执行与 Claim 入口一致的 `INSERT ... ON CONFLICT DO NOTHING`，确认该 Batch 仍为 **COMPLETED**、`attempt_count=1`，然后回滚该重复请求测试。**已证明重复领取不会重新创建 Claim。**

但这 **还不是** 完整重复运行 Airflow/Spark/Writer 的端到端幂等性验收：没有执行第二次业务 Writer COMMIT，也没有通过生产编排服务执行第二次。后续重复请求应通过 Claim `SKIP_COMPLETED` 直接短路，而不是强制调用已经存在的 Writer 事务，严禁覆盖/重新 COMMIT 本批。

## 5. 接下来真正的主线（保持 Demo 简洁）

1. **先做已入库 Batch 的独立只读业务对账与正常 Claim API `SKIP_COMPLETED` 实测**，固定 Person/Visit/map/stage/checkpoint/claim 不变。当前已执行脚本里的完整数据库对账，但需要确认 API 的正式重放边界。
2. **接入单批次 Airflow 受控 Claim→Writer 的运行执行器**；Future 自动消费需要为后续**另一个全新 S3 READY** Batch 设计，不能重复对刚正式入库的同一 Batch 作写入测试。若需验证全链路在 Airflow 自动执行，必须取得干净的新 Batch 或定义安全只读 COMPLETED 跳过路径。
3. **Legacy `etl.task004_batch_ledger.status` 仍由旧 Renderer 初始设置为 `REGISTERED`，并未在本轮 SQL 中改写成 `RECONCILED`。** 此项应独立评估是否需要版本化状态字段转换，不影响本轮 Claim Ledger COMPLETED、真 Person/Visit 和 2 VERIFIED Checkpoints 的事实，不能误称 Legacy Ledger 已 RECONCILED。
4. 双 Writer 并发压测、复杂过期 Lease/unknown-COMMIT 自动恢复继续 **FUTURE ENHANCEMENT / 不阻塞 Demo**，但仍坚持无 Source-ID 重复、单批原子事务与无半批写入。

**当前状态：TASK004 IN PROGRESS；TASK005 ON HOLD；Portal A4 HOLD。真正 OMOP业务 COMMIT 已经发生，后续不能将源 Batch 当成未入库 READY。**
